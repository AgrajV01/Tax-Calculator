import tkinter as tk
from tkinter import messagebox
import webbrowser
import requests
from bs4 import BeautifulSoup

# BC Tax Rates (Defaults)
GST_RATE = 0.05  # 5%
PST_RATE = 0.07  # 7%
INDUSTRY_TAX_RATES = {
    "Accommodation": {"PST": 0.08, "MRDT": 0.03, "url": "https://www2.gov.bc.ca/gov/content/taxes/sales-taxes/pst/publications/accommodation"},
    "Food Services": {"PST": 0.07, "MRDT": 0.00, "url": "https://www2.gov.bc.ca/gov/content/taxes/sales-taxes/pst"},
    "Energy Resources": {"PST": 0.07, "MRDT": 0.00, "url": "https://www2.gov.bc.ca/gov/content/taxes/sales-taxes/pst"}
}
BC_TAX_WEBSITE = "https://www2.gov.bc.ca/gov/content/taxes/sales-taxes/pst/charge-collect"

def fetch_industry_info():
    try:
        response = requests.get(BC_TAX_WEBSITE)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        industries = [tag.text.strip() for tag in soup.find_all('td') if tag.text.strip()]
        return industries
    except requests.RequestException:
        return []

def calculate_tax():
    try:
        product = product_entry.get()
        price = float(price_entry.get())
        industry = industry_var.get()
        
        if price < 0:
            messagebox.showerror("Input Error", "Price cannot be negative!")
            return
        
        tax_rates = INDUSTRY_TAX_RATES.get(industry, {"PST": PST_RATE, "MRDT": 0.00})
        pst = price * tax_rates["PST"]
        mrdt = price * tax_rates["MRDT"]
        gst = price * GST_RATE
        total_tax = gst + pst + mrdt
        total_price = price + total_tax
        
        result_label.config(text=f"Product: {product}\nIndustry: {industry}\nPrice: ${price:.2f}\nGST (5%): ${gst:.2f}\nPST: ${pst:.2f}\nMRDT: ${mrdt:.2f}\nTotal Tax: ${total_tax:.2f}\nFinal Price: ${total_price:.2f}")
    except ValueError:
        messagebox.showerror("Input Error", "Please enter a valid price!")

def open_industry_tax_website():
    industry = industry_var.get()
    url = INDUSTRY_TAX_RATES.get(industry, {}).get("url", BC_TAX_WEBSITE)
    webbrowser.open(url)

# GUI Setup
root = tk.Tk()
root.title("BC Tax Calculator")
root.geometry("500x400")

tk.Label(root, text="Enter Product Name:").pack(pady=5)
product_entry = tk.Entry(root)
product_entry.pack(pady=5)

tk.Label(root, text="Enter Price ($):").pack(pady=5)
price_entry = tk.Entry(root)
price_entry.pack(pady=5)

industry_var = tk.StringVar(root)
industry_var.set("Accommodation")  # Default selection
industries = fetch_industry_info() or list(INDUSTRY_TAX_RATES.keys())
tk.Label(root, text="Select Industry:").pack(pady=5)
industry_menu = tk.OptionMenu(root, industry_var, *industries)
industry_menu.pack(pady=5)

tk.Button(root, text="Calculate Tax", command=calculate_tax).pack(pady=10)
result_label = tk.Label(root, text="", justify=tk.LEFT)
result_label.pack(pady=10)

tk.Button(root, text="Industry Tax Info", command=open_industry_tax_website).pack(pady=10)
tk.Button(root, text="exit", command= root.destroy).pack(pady=12)

root.mainloop()
