import tkinter as tk
from tkinter import messagebox
import webbrowser
import requests
import os
import pandas as pd
import re  # for parsing tax rate strings
from bs4 import BeautifulSoup  # required for parsing HTML
import threading
import time

BC_TAX_WEBSITE = "https://www2.gov.bc.ca/gov/content/taxes/sales-taxes/pst/charge-collect"
HASH_FILE = "tax_info_hash.txt"

###############################################################################
# 1. LOAD EXCEL DATA
###############################################################################
try:
    df_tax = pd.read_excel("PST_information.xlsx")  # Ensure columns match: "Industry", "Category", "Items Covered", "Tax Rate", "Additional Information"
except Exception as e:
    messagebox.showerror("Error", f"Failed to load Excel file: {e}")
    # Create an empty DataFrame with the needed columns to avoid errors
    df_tax = pd.DataFrame(columns=["Industry", "Category", "Items Covered", "Tax Rate", "Additional Information"])

###############################################################################
# 2. HELPER FUNCTIONS
###############################################################################
def fetch_industry_list():
    """Return the list of Industries from the Excel file."""
    industries = df_tax["Industry"].dropna().unique().tolist()
    return industries if industries else ["No Data"]

def update_category_menu(*args):
    """Update the Category OptionMenu based on the selected Industry."""
    selected_industry = industry_var.get()
    sub_df = df_tax[df_tax["Industry"] == selected_industry]
    categories = sub_df["Category"].dropna().unique().tolist()
    if not categories:
        categories = ["No Data"]
    category_var.set(categories[0])
    category_menu["menu"].delete(0, "end")
    for cat in categories:
        category_menu["menu"].add_command(label=cat, command=tk._setit(category_var, cat))
    # Also reset items
    update_items_menu()

def update_items_menu(*args):
    """Update the Items Covered OptionMenu based on the selected Category."""
    selected_industry = industry_var.get()
    selected_category = category_var.get()
    sub_df = df_tax[
        (df_tax["Industry"] == selected_industry) &
        (df_tax["Category"] == selected_category)
    ]
    items_list = sub_df["Items Covered"].dropna().unique().tolist()
    if not items_list:
        items_list = ["No Data"]
    item_var.set(items_list[0])
    item_menu["menu"].delete(0, "end")
    for it in items_list:
        item_menu["menu"].add_command(label=it, command=tk._setit(item_var, it))

def check_for_tax_updates():
    """
    Check if the BC tax webpage has changed by comparing its last updated date.
    This is the manual version (invoked by the button) that notifies every time.
    """
    try:
        response = requests.get(BC_TAX_WEBSITE)
        response.raise_for_status()
        page_content = response.text

        # Extract the last updated date from the page content
        soup = BeautifulSoup(page_content, 'html.parser')
        last_updated_text = soup.find(text=re.compile("Last updated on"))
        
        if last_updated_text:
            # Extract the date from the text
            last_updated_date_match = re.search(r"Last updated on (\w+ \d{1,2}, \d{4})", last_updated_text)
            if last_updated_date_match:
                last_updated_date = last_updated_date_match.group(1)
                # Compare with the stored date
                if os.path.exists(HASH_FILE):
                    with open(HASH_FILE, "r") as f:
                        stored_date = f.read().strip()
                    if stored_date != last_updated_date:
                        root.after(0, lambda: messagebox.showinfo("Tax Update Notification",
                                        f"Tax information has been updated. Last updated on: {last_updated_date}."))
                        # Update the stored date
                        with open(HASH_FILE, "w") as f:
                            f.write(last_updated_date)
                    else:
                        root.after(0, lambda: messagebox.showinfo("Tax Update Notification",
                                        f"You are up to date. Last checked on: {last_updated_date}."))
                else:
                    # If no stored date, create one
                    with open(HASH_FILE, "w") as f:
                        f.write(last_updated_date)
                    root.after(0, lambda: messagebox.showinfo("Tax Update Notification",
                                        f"Tax information has been updated. Last updated on: {last_updated_date}."))
            else:
                root.after(0, lambda: messagebox.showerror("Error", "Could not find the last updated date on the webpage."))
        else:
            root.after(0, lambda: messagebox.showerror("Error", "Could not find the last updated information on the webpage."))
    except requests.RequestException:
        root.after(0, lambda: messagebox.showerror("Error", "Failed to check for tax updates."))

def check_for_tax_updates_silent():
    """
    Similar to check_for_tax_updates() but only notifies the user if an update is detected.
    This function is intended to be run periodically in the background.
    """
    try:
        response = requests.get(BC_TAX_WEBSITE)
        response.raise_for_status()
        page_content = response.text

        soup = BeautifulSoup(page_content, 'html.parser')
        last_updated_text = soup.find(text=re.compile("Last updated on"))
        
        if last_updated_text:
            last_updated_date_match = re.search(r"Last updated on (\w+ \d{1,2}, \d{4})", last_updated_text)
            if last_updated_date_match:
                last_updated_date = last_updated_date_match.group(1)
                if os.path.exists(HASH_FILE):
                    with open(HASH_FILE, "r") as f:
                        stored_date = f.read().strip()
                    if stored_date != last_updated_date:
                        # Update file and notify the user
                        with open(HASH_FILE, "w") as f:
                            f.write(last_updated_date)
                        root.after(0, lambda: messagebox.showinfo("Tax Update Notification",
                                                f"Tax information has been updated. Last updated on: {last_updated_date}."))
                else:
                    with open(HASH_FILE, "w") as f:
                        f.write(last_updated_date)
                    root.after(0, lambda: messagebox.showinfo("Tax Update Notification",
                                                f"Tax information has been updated. Last updated on: {last_updated_date}."))
    except requests.RequestException:
        # In a watcher context, we may silently pass on exceptions.
        pass

def calculate_approx_tax():
    """
    Tries to calculate an approximate tax based on the selected Industry/Category/Item
    and the entered price. If the Tax Rate is ambiguous (like '7% to 10%'),
    it notifies the user that an exact calculation isn't possible.
    """
    try:
        price = float(price_entry.get())
    except ValueError:
        messagebox.showerror("Input Error", "Please enter a valid numeric price!")
        return

    if price < 0:
        messagebox.showerror("Input Error", "Price cannot be negative!")
        return

    selected_industry = industry_var.get()
    selected_category = category_var.get()
    selected_item = item_var.get()

    # Get the row from DataFrame
    row = df_tax[
        (df_tax["Industry"] == selected_industry) &
        (df_tax["Category"] == selected_category) &
        (df_tax["Items Covered"] == selected_item)
    ]
    if row.empty:
        messagebox.showerror("Error", "No matching tax info found in the Excel for this selection.")
        return

    tax_rate_str = str(row["Tax Rate"].values[0])
    addl_info = str(row["Additional Information"].values[0])

    # Attempt to parse the tax rate string
    rates = parse_tax_rate(tax_rate_str)
    if not rates:
        messagebox.showinfo("Tax Calculation",
            f"Tax Rate: {tax_rate_str}\n"
            "This rate is ambiguous or variable. An exact calculation isn't possible.\n"
            "See 'Additional Information' or reference website for details.\n\n"
            f"Additional Info: {addl_info}")
        return

    # If parse was successful, compute approximate
    pst = price * rates["pst"] * rates["multiplier"]
    mrdt = price * rates["mrdt"] * rates["multiplier"]
    gst = price * 0.05  # 5% GST on full price

    total_tax = pst + mrdt + gst
    total_price = price + total_tax

    messagebox.showinfo("Approx. Tax Calculation",
        f"Item: {selected_item}\n"
        f"Price: ${price:.2f}\n\n"
        f"Approx PST: ${pst:.2f}\n"
        f"Approx MRDT: ${mrdt:.2f}\n"
        f"GST (5%): ${gst:.2f}\n"
        f"Total Tax: ${total_tax:.2f}\n"
        f"Final Price: ${total_price:.2f}\n\n"
        f"Tax Rate (raw): {tax_rate_str}\n"
        f"Additional Info: {addl_info}"
    )

def parse_tax_rate(tax_rate_str):
    """
    Attempt to parse a tax rate string like:
      '7% PST'
      '8% PST + 3% MRDT'
      '7% PST on 45%'
      '7% to 10%'
    Return a dict of { 'pst': 0.xx, 'mrdt': 0.xx, 'multiplier': 1.0 } or None if ambiguous.
    """
    txt = tax_rate_str.lower().strip()

    if "to" in txt or "range" in txt or "up to" in txt:
        return None

    rates = {
        "pst": 0.0,
        "mrdt": 0.0,
        "multiplier": 1.0
    }

    m = re.search(r"on\s+(\d+)%", txt)
    if m:
        portion = float(m.group(1)) / 100.0
        rates["multiplier"] = portion

    pst_match = re.findall(r"(\d+)%\s*pst", txt)
    if pst_match:
        if len(pst_match) > 1:
            return None
        rates["pst"] = float(pst_match[0]) / 100.0

    mrdt_match = re.findall(r"(\d+)%\s*mrdt", txt)
    if mrdt_match:
        if len(mrdt_match) > 1:
            return None
        rates["mrdt"] = float(mrdt_match[0]) / 100.0

    if rates["pst"] == 0.0 and rates["mrdt"] == 0.0 and rates["multiplier"] == 1.0:
        return None

    return rates

def open_tax_reference():
    """Open the BC tax reference website."""
    webbrowser.open(BC_TAX_WEBSITE)

def go_back():
    """Reset input fields to initial state."""
    price_entry.delete(0, tk.END)
    product_entry.delete(0, tk.END)
    if industry_list:
        industry_var.set(industry_list[0])
    update_category_menu()

def threaded_check_for_tax_updates():
    """Run the manual tax update check in a separate thread."""
    threading.Thread(target=check_for_tax_updates, daemon=True).start()

def update_watcher():
    """Continuously check for updates in the background."""
    # Set the interval (in seconds). For production you might use a longer interval.
    interval = 3600  # Check every hour; for testing, you could use a smaller value like 60.
    while True:
        check_for_tax_updates_silent()
        time.sleep(interval)

# Start the watcher thread so it runs in the background.
threading.Thread(target=update_watcher, daemon=True).start()

###############################################################################
# 3. GUI SETUP
###############################################################################
root = tk.Tk()
root.title("BC Tax Info (3-Level Selection)")
root.geometry("700x550")

# Product Name Input
tk.Label(root, text="Enter Product Name:").pack(pady=5)
product_entry = tk.Entry(root)
product_entry.pack(pady=5)

# Price Input
tk.Label(root, text="Enter Price ($):").pack(pady=5)
price_entry = tk.Entry(root)
price_entry.pack(pady=5)

# 1) Industry
industry_var = tk.StringVar(root)
industry_list = fetch_industry_list()
industry_var.set(industry_list[0] if industry_list else "No Data")
tk.Label(root, text="Select Industry:").pack(pady=5)
industry_menu = tk.OptionMenu(root, industry_var, *industry_list)
industry_menu.pack(pady=5)
industry_var.trace("w", update_category_menu)

# 2) Category
category_var = tk.StringVar(root)
category_var.set("No Data")
tk.Label(root, text="Select Category:").pack(pady=5)
category_menu = tk.OptionMenu(root, category_var, [])
category_menu.pack(pady=5)
category_var.trace("w", update_items_menu)

# 3) Items Covered
item_var = tk.StringVar(root)
item_var.set("No Data")
tk.Label(root, text="Select Item:").pack(pady=5)
item_menu = tk.OptionMenu(root, item_var, [])
item_menu.pack(pady=5)

# Buttons: Calculate Approx. Tax, Tax Reference, Manual Check Updates
tk.Button(root, text="Calculate Approx. Tax", command=calculate_approx_tax).pack(pady=10)
tk.Button(root, text="Tax Reference", command=open_tax_reference).pack(pady=5)
tk.Button(root, text="Check for Tax Updates", command=threaded_check_for_tax_updates).pack(pady=5)

# Go Back & Quit
nav_frame = tk.Frame(root)
nav_frame.pack(pady=10)
tk.Button(nav_frame, text="Go Back", command=go_back).pack(side=tk.LEFT, padx=10)
tk.Button(nav_frame, text="Quit", command=root.destroy).pack(side=tk.LEFT, padx=10)

# Trigger initial category & item menu updates
update_category_menu()

root.mainloop()
