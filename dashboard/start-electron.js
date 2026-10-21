const { spawn } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const appRoot = __dirname;
const electronPackage = require("electron/package.json");
const sourceExecutable = require("electron");
const sourceRoot = path.dirname(sourceExecutable);
const localAppData =
  process.env.LOCALAPPDATA || path.join(os.homedir(), "AppData", "Local");
const runtimeRoot = path.join(
  localAppData,
  "FinanceDashboard",
  "electron-runtime",
  electronPackage.version,
);
const runtimeExecutable = path.join(runtimeRoot, "electron.exe");
const runtimeMarker = path.join(runtimeRoot, ".complete");

if (!fs.existsSync(runtimeMarker)) {
  fs.mkdirSync(runtimeRoot, { recursive: true });
  fs.cpSync(sourceRoot, runtimeRoot, { recursive: true, force: true });
  fs.writeFileSync(runtimeMarker, electronPackage.version, "utf8");
}

const launcherArguments = process.argv.slice(2);
const electronArguments = launcherArguments.includes("--runtime-version")
  ? ["--version"]
  : [appRoot, ...launcherArguments];
const child = spawn(runtimeExecutable, electronArguments, {
  cwd: appRoot,
  stdio: "inherit",
  windowsHide: false,
});

child.on("error", (error) => {
  console.error(`Unable to start Electron: ${error.message}`);
  process.exitCode = 1;
});
child.on("exit", (code) => {
  process.exitCode = code ?? 1;
});
