param(
    [string]$FrontendBaseUrl = "https://wc2026-sim-ten.vercel.app",
    [string]$BackendBaseUrl = "",
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
  const backendBase = (process.env.WC2026_BACKEND_BASE_URL || "").replace(/\/$/, "");
  const timeoutMs = Number(process.env.WC2026_TIMEOUT_SEC || "45") * 1000;
  const routes = ["/", "/tournament", "/simulate", "/simulate?home=BRA&away=ARG", "/teams", "/teams/BRA", "/data-review"];
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
  const requiredTextByRoute = {
    "/tournament": ["\u6ce2\u4e71\u5019\u88dc\u30a6\u30a9\u30c3\u30c1", "\u683c\u4e0b\u52dd\u7387"],
    "/simulate": ["\u512a\u52e2\u5ea6", "\u52dd\u7387\u5dee", "xG\u5dee", "\u52dd\u6557\u8981\u56e0"],
    "/simulate?home=BRA&away=ARG": ["BRA", "ARG", "\u52dd\u6557\u8981\u56e0"],
    "/data-review": [
      "\u80fd\u529b\u5024\u5dee\u5206\u76e3\u67fb",
      "\u624b\u52d5\u88dc\u6b63",
      "JPN_NAKAMURA_K",
      "\u30d5\u30a9\u30fc\u30e1\u30fc\u30b7\u30e7\u30f3\u9069\u5408\u76e3\u67fb",
      "\u30b9\u30bf\u30e1\u30f3\u4e00\u81f4\u76e3\u67fb",
    ],
  };

  if (backendBase) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetch(`${backendBase}/api/matches/simulate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ home_team_id: "BRA", away_team_id: "ARG", seed: 20260630, allow_draw: true }),
        signal: controller.signal,
      });
      if (!response.ok) throw new Error(`sample match simulation failed with HTTP ${response.status}`);
      const match = await response.json();
      if (!match.id) throw new Error("sample match simulation did not return an id");
      routes.push(`/matches/${match.id}`);
      console.log(`sample match detail route: /matches/${match.id}`);
    } finally {
      clearTimeout(timer);
    }
  }

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
          bodyText: document.body.innerText.slice(0, 60000),
          scrollWidth: document.documentElement.scrollWidth,
          clientWidth: document.documentElement.clientWidth,
          bodyLength: document.body.innerText.trim().length,
        }));
        const status = response?.status() ?? 0;
        const badMarkers = markers.filter((marker) => metrics.bodyText.includes(marker));
        const missingRequiredText = (requiredTextByRoute[route] || []).filter((marker) => !metrics.bodyText.includes(marker));
        const hasOverflow = metrics.scrollWidth > metrics.clientWidth + 2;
        const row = `${viewport.name} ${route} status=${status} body=${metrics.bodyLength} overflow=${hasOverflow} console=${consoleErrors.length} failed=${failedRequests.length} markers=${badMarkers.length} missing=${missingRequiredText.length}`;
        console.log(row);
        if (status >= 400 || consoleErrors.length || failedRequests.length || badMarkers.length || missingRequiredText.length || hasOverflow || metrics.bodyLength < 20) {
          failures.push({
            viewport: viewport.name,
            route,
            status,
            consoleErrors,
            failedRequests,
            badMarkers: badMarkers.map((marker) => `U+${marker.codePointAt(0).toString(16).toUpperCase()}`),
            missingRequiredText,
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
    $env:WC2026_BACKEND_BASE_URL = $BackendBaseUrl
    $env:WC2026_TIMEOUT_SEC = [string]$TimeoutSec
    node $scriptPath
    if ($LASTEXITCODE -ne 0) {
        throw "Post-deploy browser smoke failed with exit code $LASTEXITCODE"
    }
} finally {
    Remove-Item Env:\WC2026_BROWSER_PATH -ErrorAction SilentlyContinue
    Remove-Item Env:\WC2026_FRONTEND_BASE_URL -ErrorAction SilentlyContinue
    Remove-Item Env:\WC2026_BACKEND_BASE_URL -ErrorAction SilentlyContinue
    Remove-Item Env:\WC2026_TIMEOUT_SEC -ErrorAction SilentlyContinue
    Pop-Location
}

Write-Host ""
Write-Host "Post-deploy browser smoke completed." -ForegroundColor Green
