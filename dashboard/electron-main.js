const { app, BrowserWindow, Menu, dialog, shell } = require("electron");
const { spawn } = require("node:child_process");
const { randomBytes } = require("node:crypto");
const http = require("node:http");
const path = require("node:path");

const DASHBOARD_URL_PATTERN = /^Finance dashboard: (http:\/\/127\.0\.0\.1:\d+\/)$/;
const HEALTH_PATH = "__finance_dashboard_health";
const HEALTH_ID = "finance-dashboard-uv-v2";
const DASHBOARD_PORT = "8765";
const smokeTest = process.argv.includes("--smoke-test");

let mainWindow;
let dashboardProcess;
let dashboardUrl;
let quitting = false;
let applicationMenu;
let menuBarVisible = true;
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
        DASHBOARD_PORT,
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

function buildAppMenu() {
  return Menu.buildFromTemplate([
    {
      label: "文件",
      submenu: [{ role: "quit", label: "退出" }],
    },
    {
      label: "视图",
      submenu: [
        { role: "reload", label: "重新加载" },
        { role: "forceReload", label: "强制重新加载" },
        { role: "toggleDevTools", label: "开发者工具" },
        { type: "separator" },
        { role: "togglefullscreen", label: "全屏" },
      ],
    },
  ]);
}

function toggleMenuBar(window) {
  if (process.platform === "darwin") {
    // macOS 的菜单栏始终显示，改为切换应用菜单。
    applicationMenu ??= Menu.getApplicationMenu();
    menuBarVisible = !menuBarVisible;
    Menu.setApplicationMenu(menuBarVisible ? applicationMenu : Menu.buildFromTemplate([]));
    return;
  }

  window.setMenuBarVisibility(!window.isMenuBarVisible());
}

function registerMenuBarShortcut(window) {
  window.webContents.on("before-input-event", (event, input) => {
    if (input.type !== "keyDown" || input.key !== "F12") {
      return;
    }
    event.preventDefault();
    if (input.isAutoRepeat || input.control || input.alt || input.meta || input.shift) {
      return;
    }
    toggleMenuBar(window);
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

  // 每个新窗口默认重新显示菜单栏。
  menuBarVisible = true;
  if (process.platform === "darwin" && applicationMenu) {
    Menu.setApplicationMenu(applicationMenu);
  }
  registerMenuBarShortcut(mainWindow);
  mainWindow.webContents.on("before-input-event", (event, input) => {
    if (input.type !== "keyDown") return;

    if (input.key === "F11" && !input.control && !input.meta && !input.alt) {
      event.preventDefault();
      mainWindow.setFullScreen(!mainWindow.isFullScreen());
      return;
    }

    // Ctrl+= / Ctrl+- 留给页面自己的缩放逻辑，这里不拦截。
    const ctrlOrCmd = input.control || (process.platform === "darwin" && input.meta);
    if (!ctrlOrCmd || input.alt) return;
    const key = input.key.toLowerCase();
    if (key === "r" && input.shift) {
      event.preventDefault();
      mainWindow.webContents.reloadIgnoringCache();
    } else if (key === "r") {
      event.preventDefault();
      mainWindow.webContents.reload();
    } else if (key === "i" && input.shift) {
      event.preventDefault();
      mainWindow.webContents.toggleDevTools();
    }
  });
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
  Menu.setApplicationMenu(buildAppMenu());
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
