from playwright.sync_api import sync_playwright, expect
import os

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()

    # Load the local HTML file
    cwd = os.getcwd()
    file_url = f"file://{cwd}/verification/mock_chat.html"
    print(f"Loading: {file_url}")
    page.goto(file_url)

    # Wait for Vue to mount and Sidebar to appear
    page.wait_for_selector(".chat-sidebar")

    # Verify Sidebar elements
    expect(page.locator(".new-chat-btn")).to_be_visible()
    expect(page.locator(".session-list")).to_be_visible()

    # Verify Session List (mocked data)
    sessions = page.locator(".session-item")
    expect(sessions).to_have_count(2)
    expect(sessions.first).to_contain_text("Invoice Query")

    # Verify Main Chat
    expect(page.locator(".chat-glass")).to_be_visible()
    expect(page.locator(".chat-input-area")).to_be_visible()

    # Test Interaction: Load Session
    sessions.first.click()
    page.wait_for_timeout(500) # Wait for mock API

    # Verify messages loaded
    messages = page.locator(".message-bubble")
    expect(messages).to_have_count(2)
    expect(messages.first).to_contain_text("Show me invoices")

    # Test Interaction: Send Message
    input_box = page.locator("input[placeholder='Ask about your ERP data...']")
    input_box.fill("What is the total?")
    page.keyboard.press("Enter")

    page.wait_for_timeout(500) # Wait for mock API

    # Verify new message added
    expect(page.locator(".message-content").last).to_contain_text("I am a mock AI response")

    # Take Screenshot
    page.screenshot(path="verification/chat_verification.png")
    print("Screenshot saved to verification/chat_verification.png")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)
