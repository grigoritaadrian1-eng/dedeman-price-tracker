from playwright.sync_api import sync_playwright

URL = "https://www.dedeman.ro/ro/gresie-exterior/-interior-portelanata-andora-sea-blue-60-x-120-cm-albastru-lucioasa-rectificata-aspect-marmura/p/4027461"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(locale="ro-RO")

    def on_request(req):
        if "__price" in req.url:
            print("\n=== __price REQUEST ===")
            print("URL:", req.url)
            try:
                data = req.post_data
                print("POST DATA:", data[:500] if data else None)
            except Exception as e:
                print("POST DATA ERROR:", e)

            print("HEADERS:", {k: req.headers[k] for k in list(req.headers) if k.lower() in ["content-type", "x-requested-with"]})
            print("=======================\n")

    page.on("request", on_request)
    page.goto(URL, wait_until="networkidle", timeout=60000)

    browser.close()
