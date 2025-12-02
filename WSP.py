import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
import time
import sys
import pandas as pd
import os
import random

# --- GUI Libraries ---
import tkinter as tk
from tkinter import simpledialog, messagebox

# --- Configuration (WSP Scraper) ---
TARGET_URL = "https://www.wsp.com/en-us/careers/job-opportunities"
OUTPUT_FILENAME = "wsp_job_listings_keyword_search.csv"
WAIT_TIMEOUT = 20

# Selectors confirmed from provided HTML
SEARCH_INPUT_ID = "Search"
SEARCH_BUTTON_SELECTOR = "button.btn.btn-primary[title='Find jobs']"
JOB_CONTAINER_SELECTOR = "div.press-result-row"
NEXT_BUTTON_SELECTOR = "a.pagenext"
COOKIE_AGREE_BUTTON_ID = "didomi-notice-agree-button"

# --- Anti-Bot Helper Functions (KEEP AS IS) ---

def human_scroll(driver):
    """Scroll the page like a human with random pauses and distances."""
    last_height = driver.execute_script("return document.body.scrollHeight")
    MAX_SCROLLS = 3 
    for _ in range(random.randint(1, MAX_SCROLLS)):
        scroll_amount = random.randint(150, 400)
        driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        time.sleep(random.uniform(0.5, 1.2))
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def random_human_action(driver):
    """Perform a small random action like clicking or moving to a random element."""
    elements = driver.find_elements(By.TAG_NAME, "a")
    if elements:
        el = random.choice(elements[:20]) 
        try:
            ActionChains(driver).move_to_element(el).pause(random.uniform(0.5, 1.0)).perform()
            if random.random() < 0.05:
                el.click()
                print("--- INFO: Performed random click action ---")
                time.sleep(random.uniform(2.0, 4.0))
                driver.back() 
                time.sleep(random.uniform(1.0, 2.0))
        except:
            pass

def random_pause(min_sec=1.5, max_sec=4.0):
    """Pauses for a random, human-like duration."""
    pause_time = random.uniform(min_sec, max_sec)
    time.sleep(pause_time)
    
# --- New Function: Cookie Handler (KEEP AS IS) ---

def handle_cookie_consent(driver, wait):
    """Attempts to find and click the 'Agree and close' cookie button."""
    print("Attempting to handle cookie consent...")
    try:
        consent_button = wait.until(
            EC.element_to_be_clickable((By.ID, COOKIE_AGREE_BUTTON_ID))
        )
        consent_button.click()
        print("✅ Cookie consent accepted.")
        time.sleep(random.uniform(1.0, 2.0))
        return True
    except TimeoutException:
        print("--- INFO: Cookie banner not found or already dismissed. Continuing. ---")
        return False
    except NoSuchElementException:
        print("--- INFO: Cookie banner element not present. Continuing. ---")
        return False
    except Exception as e:
        print(f"Warning: Error clicking cookie button: {e}")
        return False

# 🆕 NEW CORE FUNCTION: Apply Keyword Search (Modified to take keyword)
def apply_keyword_search(driver, wait, keyword):
    """Finds the search box, enters the keyword, and clicks the search button."""
    print(f"Applying keyword search for: '{keyword}'...")
    try:
        # 1. Wait for and find the search input field
        search_input = wait.until(
            EC.presence_of_element_located((By.ID, SEARCH_INPUT_ID))
        )
        
        # 2. Type the keyword
        search_input.send_keys(keyword)
        print("  ✅ Keyword entered.")
        random_pause(1.0, 2.0)
        
        # 3. Wait for and find the search button
        search_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, SEARCH_BUTTON_SELECTOR))
        )
        
        # 4. Click the search button using JavaScript for reliability
        driver.execute_script("arguments[0].click();", search_button)
        print("  ✅ Search button clicked.")
        
        # 5. Long pause for the page/job list to reload with filtered results
        random_pause(5.0, 7.0) 
        
        return True
    except TimeoutException:
        print("❌ Error: Search input or button not found within timeout.")
        return False
    except Exception as e:
        print(f"❌ Error during keyword search: {e}")
        return False

# --- Dynamic Wait Functions (KEEP AS IS) ---

def wait_for_jobs_to_load(driver, wait, page_count):
    """(Secondary Check) Waits for the job listings content to appear."""
    try:
        wait.until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, JOB_CONTAINER_SELECTOR))
        )
        return True
    except TimeoutException:
        print(f"ERROR: Job data content did not load on page {page_count} within the time limit ({WAIT_TIMEOUT}s).")
        return False

def wait_for_page_number_update(driver, wait, expected_page):
    """(Primary Check) Waits until the pagination bar's 'current' element displays the expected page number."""
    PAGE_NUMBER_SELECTOR = (By.CSS_SELECTOR, "div.pagelist.current a")
    
    try:
        wait.until(
            EC.text_to_be_present_in_element(PAGE_NUMBER_SELECTOR, str(expected_page))
        )
        print(f"✅ Confirmed page loaded: Pagination bar shows Page {expected_page}.")
        return True
    except TimeoutException:
        print(f"ERROR: Pagination bar failed to confirm Page {expected_page} within timeout.")
        return False
    except Exception as e:
        print(f"Error during page number confirmation: {e}")
        return False


def click_numeric_page_link(driver, wait, target_page):
    """Attempts to click the numeric page link with built-in retry logic."""
    NUMERIC_LINK_SELECTOR = f"a[name='page'][data-value='{target_page}']"
    MAX_CLICK_RETRIES = 3
    retries = 0

    while retries < MAX_CLICK_RETRIES:
        try:
            print(f"Attempting fallback: Clicking numeric link for Page {target_page} (Try {retries+1}/{MAX_CLICK_RETRIES})...")
            
            numeric_link = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, NUMERIC_LINK_SELECTOR))
            )
            
            driver.execute_script("arguments[0].scrollIntoView(true);", numeric_link)
            driver.execute_script("arguments[0].click();", numeric_link)
            
            return True

        except (TimeoutException, StaleElementReferenceException) as e:
            retries += 1
            if retries < MAX_CLICK_RETRIES:
                print(f"  Warning: Element not ready or stale. Retrying click...")
                time.sleep(1)
            else:
                print(f"Error: Numeric link for Page {target_page} not found or not clickable after {MAX_CLICK_RETRIES} attempts.")
                return False
        except Exception as e:
            print(f"Error clicking numeric link for Page {target_page}: {e}")
            return False
    return False 


# --- Main Scraper Function (Modified to take inputs) ---

def run_scraper(keyword, max_pages):
    """Initializes the browser, handles filtering, pagination, scrapes job data, and saves incrementally."""
    
    # 🎯 Use the inputs from the GUI
    SEARCH_KEYWORD = keyword 
    MAX_PAGES = max_pages
    
    print(f"--- SCRAPER CONFIGURATION ---")
    print(f"Keyword: {SEARCH_KEYWORD}")
    print(f"Max Pages: {MAX_PAGES}")
    print("Starting undetected Chrome...")
    
    driver = None
    file_exists = os.path.isfile(OUTPUT_FILENAME)
    
    try:
        driver = uc.Chrome()
        driver.maximize_window()
        
        print(f"Opening URL: {TARGET_URL}")
        driver.get(TARGET_URL)
        wait = WebDriverWait(driver, WAIT_TIMEOUT)
        
        # 1. Handle the Cookie Consent Banner
        handle_cookie_consent(driver, wait)
        
        # 2. Apply Keyword Search
        if not apply_keyword_search(driver, wait, SEARCH_KEYWORD):
            print("Failed to apply keyword filter successfully. Proceeding without search.")
            # If search fails, the script continues on the unfiltered page 1
        
        page_count = 1
        
        if not wait_for_jobs_to_load(driver, wait, page_count):
            print("Could not load initial page data. Exiting.")
            return

        # 3. Start main pagination and scraping loop (Scraping until MAX_PAGES/End)
        while page_count <= MAX_PAGES:
            print(f"\n--- Processing Page {page_count} ---")
            current_page_jobs = [] 
            
            # --- DATA EXTRACTION LOGIC ---
            MAX_RETRIES = 3
            retries = 0

            while retries < MAX_RETRIES:
                try:
                    job_elements = driver.find_elements(By.CSS_SELECTOR, JOB_CONTAINER_SELECTOR)
                    print(f"Found {len(job_elements)} job listings on this page.")
                    
                    if len(job_elements) == 0 and page_count > 1:
                        raise StaleElementReferenceException("Job list is empty/stale, forcing retry.")

                    for job in job_elements:
                        # ... (Rest of the data extraction logic remains the same)
                        title = "Title Not Found"
                        location = "Location Not Found"
                        link = ""
                        
                        try:
                            link_element = job.find_element(By.CSS_SELECTOR, "a.career-result-link")
                            link = link_element.get_attribute("href")
                            
                            try:
                                title_element = link_element.find_element(By.CSS_SELECTOR, "h2.typo__24_20")
                                title = title_element.text.strip()
                            except:
                                title = link_element.text.strip() if link_element.text.strip() else "Title Missing - Check Link"
                                
                            try:
                                location_element = job.find_element(By.CSS_SELECTOR, "div.text.text-locations")
                                location = location_element.text.strip()
                            except:
                                pass 

                            current_page_jobs.append({
                                "Title": title, 
                                "Location": location, 
                                "Link": link, 
                                "Page": page_count,
                                "Search Keyword": SEARCH_KEYWORD # Added keyword field
                            })
                            
                        except StaleElementReferenceException as se:
                            raise se 
                        
                        except Exception:
                            continue
                            
                    break 

                except StaleElementReferenceException:
                    retries += 1
                    print(f"Stale element encountered on page {page_count}. Retrying... (Attempt {retries}/{MAX_RETRIES})")
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"Error during job extraction on page {page_count}: {e}. Giving up extraction after {retries} retries.")
                    break 

            # --- Incremental Save & Anti-Bot Actions ---
            if current_page_jobs:
                df_page = pd.DataFrame(current_page_jobs)
                write_header = not file_exists and page_count == 1
                df_page.to_csv(OUTPUT_FILENAME, mode='a', header=write_header, index=False)
                print(f"✅ Data for page {page_count} saved to {OUTPUT_FILENAME}.")
                file_exists = True 
            
            # 🤖 ANTI-BOT MEASURES
            human_scroll(driver)
            random_human_action(driver)
            random_pause(1.5, 3.5) 


            # --- PAGINATION LOGIC ---
            clicked_successfully = False
            next_page = page_count + 1

            # --- Attempt 1: Click the 'Next' Arrow ---
            try:
                next_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, NEXT_BUTTON_SELECTOR)))
                driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                driver.execute_script("arguments[0].click();", next_button)
                print(f"Clicking 'Next' arrow (to load page {next_page})...")
                clicked_successfully = True
            except:
                pass

            # --- Attempt 2: Click the Numeric Link (Fallback with retry) ---
            if not clicked_successfully:
                if click_numeric_page_link(driver, wait, next_page):
                    clicked_successfully = True
                else:
                    print("End of pagination reached: Cannot find 'Next' button or numeric link.")
                    break # Stop the while loop

            # --- Check and Continue ---
            if clicked_successfully:
                
                # Wait for the pagination bar to update
                if not wait_for_page_number_update(driver, wait, next_page):
                    print(f"Stopping: Failed to confirm navigation to Page {next_page}.")
                    break
                    
                page_count += 1
                
                # Wait for the job *content* to load
                if not wait_for_jobs_to_load(driver, wait, page_count):
                    print("Next page data failed to load. Stopping.")
                    break
            else:
                break 
                
    except Exception as e:
        print(f"A general error occurred: {e}")
        
    finally:
        if driver:
            print(f"\n--- SCRAPING PROCESS FINISHED ---")
            print("The browser is still open. Press ENTER to close it.")
            input() 
            driver.quit()
            print("Browser closed.")
            sys.exit(0)
            
# 🚀 New GUI Logic to gather inputs
def get_user_input():
    # Create the root window (hidden)
    root = tk.Tk()
    root.withdraw() 

    try:
        # Get Keyword
        keyword = simpledialog.askstring(
            "WSP Scraper Setup", 
            "Enter the **SEARCH KEYWORD** (e.g., 'United States', 'Engineer', 'Remote'):"
        )
        if not keyword:
            messagebox.showinfo("Cancelled", "Scraping cancelled by user.")
            sys.exit(0)

        # Get Max Pages
        max_pages_str = simpledialog.askstring(
            "WSP Scraper Setup", 
            "Enter the **MAXIMUM NUMBER OF PAGES** to scrape (e.g., 10, or 999 for all pages):",
            initialvalue="10"
        )
        
        if not max_pages_str:
            messagebox.showinfo("Cancelled", "Scraping cancelled by user.")
            sys.exit(0)
            
        try:
            max_pages = int(max_pages_str)
            if max_pages <= 0:
                messagebox.showerror("Invalid Input", "The number of pages must be a positive integer.")
                sys.exit(1)
        except ValueError:
            messagebox.showerror("Invalid Input", "The number of pages must be a valid integer.")
            sys.exit(1)

        # Run the scraper with the gathered inputs
        run_scraper(keyword, max_pages)

    except Exception as e:
        messagebox.showerror("Error", f"An unexpected error occurred during GUI setup: {e}")
    finally:
        root.destroy()


if __name__ == "__main__":
    try:
        import pandas as pd
        get_user_input()
    except ImportError:
        print("\n--- ERROR ---")
        print("The script requires the **pandas** library to save the data to CSV.")
        print("Please install it: `pip install pandas`")
        print("--------------------------------------------------")
