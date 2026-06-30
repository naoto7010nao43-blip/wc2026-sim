param(
    [string]$FrontendBaseUrl = "https://wc2026-sim-ten.vercel.app",
    [int]$TimeoutSec = 45,
    [switch]$SkipPlaywrightInstall
)

$ErrorActionPreference = "Stop"

$edgeCandidates = @(
    "C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
)
$browserPath = $edgeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $browserPath) {
    throw "No Edge/Chrome executable found for browser smoke."
}

$tmp = Join-Path $env:TEMP "wc2026-playwright-smoke"
New-Item -ItemType Directory -Force -Path $tmp | Out-Null

if (-not (Test-Path (Join-Path $tmp "package.json"))) {
    Push-Location $tmp
    try {
        npm init -y | Out-Null
    } finally {
        Pop-Location
    }
}

if (-not $SkipPlaywrightInstall -and -not (Test-Path (Join-Path $tmp "node_modules\playwright"))) {
    Push-Location $tmp
    try {
        npm install playwright@latest | Out-Null
    } finally {
        Pop-Location
    }
}

$scriptPath = Join-Path $tmp "wc2026-browser-smoke.cjs"
$js = @'
(async () => {
  const { chromium } = require("playwright");
  const browserPath = process.env.WC2026_BROWSER_PATH;
  const base = process.env.WC2026_FRONTEND_BASE_URL.replace(/\/$/, "");
  const timeoutMs = Number(process.env.WC2026_TIMEOUT_SEC || "45") * 1000;
  const routes = ["/", "/tournament", "/simulate", "/teams", "/teams/BRA", "/data-review"];
  const viewports = [
    { name: "desktop", width: 1280, height: 900 },
    { name: "mobile", width: 390, height: 844 },
  ];
  const markers = [
    String.fromCodePoint(0xfffd),
    String.fromCodePoint(0x7e3a),
    String.fromCodePoint(0x7e67),
    String.fromCodePoint(0x8b41),
    String.fromCodePoint(0x00c3),
    String.fromCodePoint(0x00e3),
  ];

  const browser = await chromium.launch({ executablePath: browserPath, headless: true });
  const failures = [];
  try {
    for (const viewport of viewports) {
      for (const route of routes) {
        const page = await browser.newPage({ viewport: { width: viewport.width, height: viewport.height } });
        const consoleErrors = [];
        const failedRequests = [];
        page.on("console", (msg) => {
          if (msg.type() === "error") consoleErrors.push(msg.text());
        });
        page.on("requestfailed", (req) => {
          failedRequests.push(`${req.method()} ${req.url()} ${req.failure()?.errorText || ""}`);
        });

        const response = await page.goto(base + route, { waitUntil: "domcontentloaded", timeout: timeoutMs });
        await page.waitForLoadState("load", { timeout: timeoutMs }).catch(() => {});
        await page.waitForTimeout(2500);
        const metrics = await page.evaluate(() => ({
          bodyText: document.body.innerText.slice(0, 20000),
          scrollWidth: document.documentElement.scrollWidth,
          clientWidth: document.documentElement.clientWidth,
          bodyLength: document.body.innerText.trim().length,
        }));
        const status = response?.status() ?? 0;
        const badMarkers = markers.filter((marker) => metrics.bodyText.includes(marker));
        const hasOverflow = metrics.scrollWidth > metrics.clientWidth + 2;
        const row = `${viewport.name} ${route} status=${status} body=${metrics.bodyLength} overflow=${hasOverflow} console=${consoleErrors.length} failed=${failedRequests.length} markers=${badMarkers.length}`;
        console.log(row);
        if (status >= 400 || consoleErrors.length || failedRequests.length || badMarkers.length || hasOverflow || metrics.bodyLength < 20) {
          failures.push({
            viewport: viewport.name,
            route,
            status,
            consoleErrors,
            failedRequests,
            badMarkers: badMarkers.map((marker) => `U+${marker.codePointAt(0).toString(16).toUpperCase()}`),
            hasOverflow,
            widths: [metrics.scrollWidth, metrics.clientWidth],
            bodyLength: metrics.bodyLength,
          });
        }
        await page.close();
      }
    }
  } finally {
    await browser.close();
  }
  if (failures.length) {
    console.log(JSON.stringify(failures, null, 2));
    process.exit(1);
  }
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
'@
[System.IO.File]::WriteAllText($scriptPath, $js, [System.Text.Encoding]::UTF8)

Push-Location $tmp
try {
    $env:WC2026_BROWSER_PATH = $browserPath
    $env:WC2026_FRONTEND_BASE_URL = $FrontendBaseUrl
    $env:WC2026_TIMEOUT_SEC = [string]$TimeoutSec
    node $scriptPath
} finally {
    Remove-Item Env:\WC2026_BROWSER_PATH -ErrorAction SilentlyContinue
    Remove-Item Env:\WC2026_FRONTEND_BASE_URL -ErrorAction SilentlyContinue
    Remove-Item Env:\WC2026_TIMEOUT_SEC -ErrorAction SilentlyContinue
    Pop-Location
}

Write-Host ""
Write-Host "Post-deploy browser smoke completed." -ForegroundColor Green
