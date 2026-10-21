const { app, BrowserWindow, dialog, shell } = require("electron");
const { spawn } = require("node:child_process");
const { randomBytes } = require("node:crypto");
const http = require("node:http");
const path = require("node:path");

const DASHBOARD_URL_PATTERN = /^Finance dashboard: (http:\/\/127\.0\.0\.1:\d+\/)$/;
const HEALTH_PATH = "__finance_dashboard_health";
const HEALTH_ID = "finance-dashboard-uv-v2";
const smokeTest = process.argv.includes("--smoke-test");

let mainWindow;
let dashboardProcess;
let dashboardUrl;
let quitting = false;
const shutdownToken = randomBytes(24).toString("hex");

function waitForDashboard(url, attempts = 60) {
  return new Promise((resolve, reject) => {
    const check = (remaining) => {
      const request = http.get(new URL(HEALTH_PATH, url), (response) => {
        let body = "";
        response.setEncoding("utf8");
        response.on("data", (chunk) => {
          body += chunk;
        });
        response.on("end", () => {
          if (response.statusCode === 200 && body === HEALTH_ID) {
            resolve();
          } else if (remaining > 1) {
            setTimeout(() => check(remaining - 1), 250);
          } else {
            reject(new Error("Dashboard health check failed."));
          }
        });
      });
      request.setTimeout(1000, () => request.destroy());
      request.on("error", () => {
        if (remaining > 1) {
          setTimeout(() => check(remaining - 1), 250);
        } else {
          reject(new Error("Dashboard server did not become ready."));
        }
      });
    };
    check(attempts);
  });
}

function startDashboard() {
  return new Promise((resolve, reject) => {
    const dashboardRoot = __dirname;
    let output = "";
    let settled = false;

    dashboardProcess = spawn(
      "uv",
      [
        "run",
        "--project",
        dashboardRoot,
        "python",
        "-u",
        path.join(dashboardRoot, "dashboard_server.py"),
        "--port",
        "0",
        "--no-browser",
      ],
      {
        cwd: dashboardRoot,
        env: {
          ...process.env,
          FINANCE_DATA_ROOT: path.resolve(dashboardRoot, ".."),
          FINANCE_DASHBOARD_SHUTDOWN_TOKEN: shutdownToken,
        },
        windowsHide: true,
      },
    );

    const fail = (error) => {
      if (!settled) {
        settled = true;
        reject(error);
      }
    };

    dashboardProcess.stdout.setEncoding("utf8");
    dashboardProcess.stdout.on("data", async (chunk) => {
      if (smokeTest) process.stderr.write(`[dashboard stdout] ${chunk}`);
      output += chunk;
      const lines = output.split(/\r?\n/);
      output = lines.pop() || "";
      for (const line of lines) {
        const match = line.trim().match(DASHBOARD_URL_PATTERN);
        if (!match || settled) continue;
        try {
          if (smokeTest) process.stderr.write(`[dashboard url] ${match[1]}\n`);
          await waitForDashboard(match[1]);
          if (smokeTest) process.stderr.write("[dashboard ready]\n");
          settled = true;
          resolve(match[1]);
        } catch (error) {
          fail(error);
        }
      }
    });

    dashboardProcess.stderr.setEncoding("utf8");
    dashboardProcess.stderr.on("data", (chunk) => {
      process.stderr.write(chunk);
    });
    dashboardProcess.on("error", (error) => {
      fail(
        error.code === "ENOENT"
          ? new Error("找不到 uv，请先安装 uv 并确保它已加入 PATH。")
          : error,
      );
    });
    dashboardProcess.on("exit", (code) => {
      dashboardProcess = undefined;
      if (!quitting) {
        const error = new Error(
          `Dashboard 服务意外退出（退出码 ${code ?? "unknown"}）。`,
        );
        if (settled) {
          dialog.showErrorBox("金融数据终端服务已停止", error.message);
          app.quit();
        } else {
          fail(error);
        }
      }
    });
  });
}

function stopDashboard() {
  return new Promise((resolve) => {
    if (!dashboardProcess || !dashboardUrl) {
      if (dashboardProcess && !dashboardProcess.killed) dashboardProcess.kill();
      resolve();
      return;
    }

    const processToStop = dashboardProcess;
    const finish = () => {
      clearTimeout(forceTimer);
      resolve();
    };
    const forceTimer = setTimeout(() => {
      if (!processToStop.killed) processToStop.kill();
      resolve();
    }, 3000);
    processToStop.once("exit", finish);

    const shutdownUrl = new URL("__finance_dashboard_shutdown", dashboardUrl);
    shutdownUrl.searchParams.set("token", shutdownToken);
    const request = http.request(shutdownUrl, { method: "POST" }, (response) => {
      response.resume();
    });
    request.setTimeout(1000, () => request.destroy());
    request.on("error", () => {
      if (!processToStop.killed) processToStop.kill();
    });
    request.end();
  });
}

function createWindow(url) {
  mainWindow = new BrowserWindow({
    title: "全球金融数据终端",
    width: 1600,
    height: 1000,
    minWidth: 1100,
    minHeight: 700,
    show: false,
    backgroundColor: "#07111f",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  mainWindow.removeMenu();
  if (smokeTest) {
    mainWindow.webContents.once("did-finish-load", () => app.quit());
  } else {
    mainWindow.once("ready-to-show", () => mainWindow.show());
  }
  mainWindow.webContents.setWindowOpenHandler(({ url: target }) => {
    if (target.startsWith("https://") || target.startsWith("http://")) {
      void shell.openExternal(target);
    }
    return { action: "deny" };
  });
  mainWindow.webContents.on("will-navigate", (event, target) => {
    if (target !== url) event.preventDefault();
  });
  void mainWindow.loadURL(url);
}

app.whenReady().then(async () => {
  try {
    dashboardUrl = await startDashboard();
    createWindow(dashboardUrl);
  } catch (error) {
    dialog.showErrorBox("金融数据终端启动失败", error.message);
    app.quit();
  }
});

app.on("before-quit", (event) => {
  if (quitting) return;
  event.preventDefault();
  quitting = true;
  void stopDashboard().finally(() => app.quit());
});

app.on("window-all-closed", () => app.quit());
