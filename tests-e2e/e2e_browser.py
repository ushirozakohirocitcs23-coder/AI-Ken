"""End-to-end browser test of the main user and administrator workflows.

Run the backend first with the test-only mock LLM (no API key needed):
  cd backend
  APP_ENV=test LLM_PROVIDER=mock ADMIN_EMAIL=admin@example.org ADMIN_PASSWORD=AdminPass123 \
    DATABASE_URL=sqlite:///./data/e2e.db uvicorn app.main:app --port 8000
Then (after `npm run build` in frontend/ and `playwright install chromium`):
  python tests-e2e/e2e_browser.py        # screenshots go to ./e2e-screens/
"""
import os
import re, sys, time
from playwright.sync_api import sync_playwright, expect

BASE = "http://localhost:8000"
OUT = "e2e-screens/"
os.makedirs(OUT, exist_ok=True)
errors = []
EMAIL = f"ken{int(time.time())}@example.com"

def shot(page, name):
    page.screenshot(path=OUT + name + ".png", full_page=False)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1366, "height": 860}, bypass_csp=True)
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    page.on("pageerror", lambda e: errors.append(str(e)))

    page.goto(BASE); page.wait_for_timeout(1800); shot(page, "01_landing")
    # protected route redirect
    page.goto(BASE + "/app"); page.wait_for_url("**/login"); print("redirect to login ok")
    # register validation
    page.goto(BASE + "/register")
    page.get_by_role("button", name="Create account").click()
    expect(page.get_by_text("Please enter your full name.")).to_be_visible()
    page.get_by_label("Full name").fill("Ken Lontoc")
    page.get_by_label("Email").fill(EMAIL)
    page.get_by_label("Password", exact=True).fill("Secret123")
    page.get_by_label("Confirm password").fill("Secret123")
    page.get_by_role("button", name="Create account").click()
    page.wait_for_url("**/app"); page.wait_for_timeout(800); shot(page, "02_dashboard")
    expect(page.get_by_text("Every feeling has a story")).to_be_visible()

    # open settings, pick Filipino + Tanaga
    page.get_by_role("button", name=re.compile("Auto language")).click()
    page.get_by_label("Language").select_option("fil")
    page.get_by_label("Poem type").select_option("tanaga")
    page.wait_for_timeout(300); shot(page, "03_settings")
    page.get_by_role("button", name="Close settings").click()
    box = page.get_by_label("Your story")
    box.fill("Masaya ako kapag kasama ko ang pamilya ko, pero minsan nalulungkot ako kapag iniisip ko ang mga pangarap na hindi ko pa naaabot.")
    box.press("Enter")
    page.wait_for_url(re.compile(r".*/app/c/\d+"), timeout=20000)
    page.wait_for_selector("article", timeout=20000); page.wait_for_timeout(600)
    shot(page, "04_poem")
    art = page.locator("article").first
    expect(art.get_by_text("Tanaga").first).to_be_visible()
    art.get_by_role("button", name="Validation").click(); page.wait_for_timeout(300); shot(page, "05_validation")
    expect(art.get_by_text("Syllable pattern")).to_be_visible()
    art.get_by_role("button", name="Vocabulary").click(); page.wait_for_timeout(300)
    expect(art.get_by_text("ligaya", exact=True)).to_be_visible(); shot(page, "06_vocab")
    art.get_by_role("button", name="Save poem").click(); page.wait_for_timeout(500)
    art.get_by_role("radio", name="4 stars").click(); page.wait_for_timeout(400)
    # translate
    art.get_by_role("button", name="To English").click()
    page.wait_for_function("document.querySelectorAll('article').length >= 2", timeout=20000)
    # regenerate
    page.locator("article").first.get_by_role("button", name="Regenerate").click()
    page.wait_for_function("document.querySelectorAll('article').length >= 3", timeout=20000)
    page.wait_for_timeout(500); shot(page, "07_after_actions")
    # Shift+Enter makes a newline, not a send
    box.fill("line one"); box.press("Shift+Enter"); box.type("line two")
    assert "\n" in box.input_value(), "shift+enter newline"
    box.fill("")
    # saved poems
    page.get_by_role("link", name="My Saved Poems").click(); page.wait_for_timeout(800)
    expect(page.locator("article")).to_have_count(1); shot(page, "08_saved")
    # profile
    page.get_by_role("link", name="Profile & Settings").click(); page.wait_for_timeout(500); shot(page, "09_profile")
    # logout
    page.get_by_role("button", name="Log out").first.click(); page.wait_for_url("**/login")
    page.goto(BASE + "/app/saved"); page.wait_for_url("**/login"); print("post-logout protection ok")

    # forgot password (dev link)
    page.goto(BASE + "/forgot-password"); page.get_by_label("Email").fill(EMAIL)
    page.get_by_role("button", name="Send reset link").click(); expect(page.get_by_text("Development mode", exact=True)).to_be_visible()

    # admin
    page.goto(BASE + "/login")
    page.get_by_label("Email").fill("admin@example.org"); page.get_by_label("Password", exact=True).fill("AdminPass123")
    page.get_by_role("button", name="Log in").click(); page.wait_for_url("**/admin"); page.wait_for_timeout(1500)
    shot(page, "10_admin_dashboard")
    for path, name in [("users", "11_users"), ("knowledge", "12_knowledge"), ("forms", "13_forms"), ("dictionary", "14_dictionary"),
                       ("analytics", "15_analytics"), ("settings", "16_settings"), ("audit", "17_audit")]:
        page.goto(f"{BASE}/admin/{path}"); page.wait_for_timeout(1300); shot(page, name)
    # upload a KB doc by paste
    page.goto(BASE + "/admin/knowledge"); page.wait_for_timeout(800)
    page.get_by_role("button", name="Add document").click()
    dlg = page.get_by_role("dialog")
    dlg.get_by_label("Title").fill("Kundiman notes")
    dlg.get_by_label("…or paste text").fill("Ang kundiman ay awit ng pag-ibig at pangungulila. Larawang-diwa: buwan, harana, gitara.")
    dlg.get_by_role("button", name="Upload & process").click()
    expect(page.get_by_text("Kundiman notes").first).to_be_visible(timeout=10000)
    page.get_by_role("button", name="Search", exact=True).click(); page.wait_for_timeout(800); shot(page, "18_kb_after_upload")
    # user admin -> user cannot access admin
    page.get_by_role("button", name="Log out").click(); page.wait_for_url("**/login")
    page.get_by_label("Email").fill(EMAIL); page.get_by_label("Password", exact=True).fill("Secret123")
    page.get_by_role("button", name="Log in").click(); page.wait_for_url("**/app")
    page.goto(BASE + "/admin"); page.wait_for_timeout(800); assert "/admin" not in page.url, page.url
    print("user blocked from admin ok")

    # mobile
    m = b.new_context(viewport={"width": 390, "height": 844}, storage_state=ctx.storage_state())
    mp = m.new_page(); mp.goto(BASE + "/app"); mp.wait_for_timeout(1200); shot(mp, "19_mobile_chat")
    mp.get_by_role("button", name="Open menu").click(); mp.wait_for_timeout(400); shot(mp, "20_mobile_menu")
    mp.goto(BASE); mp.wait_for_timeout(1500); shot(mp, "21_mobile_landing")
    b.close()

print("CONSOLE ERRORS:", errors)
