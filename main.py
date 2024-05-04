import tkinter as tk
from tkinter import ttk
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import pyperclip
import threading
from datetime import datetime
import random

ANY_ITEM_KEY = "<ANY_ITEM>"

CURRENT_OFFERS = "https://www.realmeye.com/current-seasonal-offers"

RECENT_SEASONAL_OFFERS = "https://www.realmeye.com/recent-seasonal-offers"

USER_AGENTS_POOL = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Avira/123.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 OPR/109.0.0.0 (Edition utorrent)',
    'Mozilla/5.0 (Windows NT 10.0; Win64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6314.205 Safari/537.36 OPR/104.0.4502.172',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0'
]


# Getting all the page info into df
def fetch_listings():
    """
    Scrapes the recent seasonal offers page and
    turns the listing table into a pandas dataframe
    :return: A dataframe containing all recent trade listings
    """
    headers = {'user-agent': get_random_ua()}
    response = requests.get(RECENT_SEASONAL_OFFERS, headers=headers)
    if response.status_code != 200:
        raise Exception("Error fetching listings:" + response.text)
    html_content = response.text
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table', class_='table tablesorter')
    sell_items = []
    sell_quant = []
    buy_items = []
    buy_quant = []
    times = []
    seller = []
    # Check if the table is found
    if table:
        # Iterate through each row (tr) in the table
        for row in table.find_all('tr'):
            # Iterate through each cell (td) in the row
            cells = row.find_all('td')
            # Extract and print the text from each cell
            if cells:
                sell_item = cells[0].find('span', class_='item')['data-item']
                num_sell = re.sub(r'\D', '', sell_item)
                sell_items.append(num_sell)
                sell_quant.append(cells[0].find('span', class_='item-quantity-static').text.strip('×'))
                buy_item = cells[1].find('span', class_='item')['data-item']
                num_buy = re.sub(r'\D', '', buy_item)
                buy_items.append(num_buy)
                buy_quant.append(cells[1].find('span', class_='item-quantity-static').text.strip('×'))
                time = cells[2].find('span', class_='muted')
                if time:
                    times.append(cells[2].find('span', class_='muted').text.strip())
                else:
                    times.append(cells[2].find('strong').text.strip())
                seller.append(cells[5].find('a').text.strip())
        dict = {"sell_item": sell_items,
                "s_quant": sell_quant,
                "buy_item": buy_items,
                "b_quant": buy_quant,
                "times": times,
                "seller": seller
                }
        df = pd.DataFrame(dict)
    return df


# Getting a dictionary of number:name
def fetch_items():
    """
    Scrapes the seasonal offers page to get tradable items
    :return: A dictionary with item_id:item_title
    """
    headers = {'user-agent': get_random_ua()}
    response = requests.get(CURRENT_OFFERS, headers=headers)
    html_content = response.text
    df = pd.DataFrame()
    if response.status_code != 200:
        raise Exception("Error fetching items dictionary:" + response.text)
    soup = BeautifulSoup(html_content, 'html.parser')
    items_by_id = {ANY_ITEM_KEY: "Any item"}
    current_offers_div = soup.find('div', class_='current-offers')
    if current_offers_div:
        item_wrappers = current_offers_div.find_all('span', class_='item-wrapper')
        for item_wrapper in item_wrappers:
            href = ""
            item_selling = item_wrapper.find('a', class_='item-selling')
            item_buying = item_wrapper.find('a', class_='item-buying')
            if item_selling:
                href = item_selling['href']
            elif item_buying:
                href = item_buying['href']
            if href:
                # href example /offers-to/sell/-112?seasonal"
                item_id = re.sub("[^0-9]", "", href)
                item_span = item_wrapper.find('span', class_='item')
                title = item_span['title']
                items_by_id[item_id] = title

    return items_by_id


def get_random_ua():
    """
    :return: Random user agent from a pool of fixed user agents
    """
    randnum = random.randint(0, len(USER_AGENTS_POOL) - 1)
    return USER_AGENTS_POOL[randnum]


def fetch_data():
    """
    Using fetch_items and fetch_listings to fill the global variables item_dict and listings_df
    """
    global item_dict, listings_df
    item_dict = fetch_items()
    listings_df = fetch_listings()


def fetch_and_update():
    """
    Fetching data and updating the time label text
    """
    fetch_data()
    update_time_label()


def get_time():
    """
    :return: Current system time in H:M:S format
    """
    current_time = datetime.now()
    return current_time.strftime("%H:%M:%S")


def update_time_label():
    """
    Changes the text of update time label to the current time
    """
    lupdate_time_label.config(text=get_time())


def filter_listings():
    """
    Takes the user inputs in the comboboxes and search for them
    in the listings dataframe. The relevant rows are inserted into a new dataframe
    :return: A dataframe including only the relevant listings
    """
    global tell_string
    tell_string = ""
    sell_item_input = sell_combo.get()
    buy_item_input = buy_combo.get()
    # Get the item numbers corresponding to the selected item titles
    sell_item = None
    buy_item = None
    for key, value in item_dict.items():
        if value == sell_item_input:
            sell_item = key
        if value == buy_item_input:
            buy_item = key

    if sell_item and buy_item:
        # Filter relevant listings based on selected item numbers
        if sell_item == ANY_ITEM_KEY:
            relevant_listings = listings_df[(listings_df['sell_item'] == buy_item)]
        elif buy_item == ANY_ITEM_KEY:
            relevant_listings = listings_df[(listings_df['buy_item'] == sell_item)]
        else:
            relevant_listings = listings_df[
                (listings_df['sell_item'] == buy_item) & (listings_df['buy_item'] == sell_item)]
        # Display relevant listings in the text widget
        results_text.delete(1.0, tk.END)  # Clear previous results
        if not relevant_listings.empty:
            for index in relevant_listings.index:
                seller = listings_df.loc[index, 'seller']
                item_to_buy = listings_df.loc[index, 'buy_item']
                item_to_sell = listings_df.loc[index, 'sell_item']
                quant_buy = listings_df.loc[index, 'b_quant']
                quant_sell = listings_df.loc[index, 's_quant']
                times = listings_df.loc[index, 'times']
                string = f"{seller} wants to sell {item_dict[item_to_sell]} x{quant_sell} for {item_dict[item_to_buy]} x{quant_buy}. {times} sets"
                results_text.insert(tk.END, string + '\n')
                if tell_string == "":
                    tell_string = f"/tell {seller} Hi, I would like to buy your {quant_sell} {item_dict[item_to_sell]} for my {quant_buy} {item_dict[item_to_buy]}"
        else:
            results_text.insert(tk.END, "No relevant listings found.")
    else:
        results_text.delete(1.0, tk.END)
        results_text.insert(tk.END, "Invalid item selection.")


def on_checkbox_clicked():
    """
    Enabling/Disabling live search. When live search is active
    fetching data will occur every 10 seconds and other widgets on the screen
    will be disabled.
    """
    global live_search_enabled
    if chk_state.get():
        live_search_enabled = True
        disable_widgets()
        thread = threading.Thread(target=schedule_update)
        thread.start()
    else:
        live_search_enabled = False
        enable_widgets()


def disable_widgets():
    """
    Disables all widgets on the screen except the checkbox and the textarea
    """
    sell_combo.configure(state='disabled')
    buy_combo.configure(state='disabled')
    fetch_button.configure(state='disabled')
    refresh_button.configure(state='disabled')


def enable_widgets():
    """
    Enables all widgets on the screen except the checkbox and the textarea
    (since they are always enabled)
    """
    sell_combo.configure(state='normal')
    buy_combo.configure(state='normal')
    fetch_button.configure(state='normal')
    refresh_button.configure(state='normal')


def schedule_update():
    """
    Updating the data using threading so the UI will stay smooth
    """
    if live_search_enabled:
        fetch_data()
        update_time_label()
        filter_listings()
        root.after(10000, schedule_update)


def on_right_click(event):
    """
    Copies a ready to send /tell message to the user's clipboard if
    the listing is valid.
    :param event:
    """
    if tell_string != '':
        pyperclip.copy(tell_string)
        results_text.insert(tk.END, "\n/tell message copied to clipboard !")
    else:
        results_text.insert(tk.END, "\nA result is needed in order to copy to clipboard")


def sell_search(event):
    """
    Search function suited for the sell combobox
    :param event:
    """
    search(event, sell_combo)


def buy_search(event):
    """
    Search function suited for the buy combobox
    :param event:
    """
    search(event, buy_combo)


def search(event, combo_box):
    """
    Essentially making the combobox into a semi-autocomplete box where
    you have to type and then open the combobox options to look for a fit.
    :param event:
    :param combo_box:
    """
    value = event.widget.get()
    if value == '':
        combo_box['values'] = list(item_dict.values())
    else:
        data = []
        for item in list(item_dict.values()):
            if value.lower() in item.lower():
                data.append(item)
        combo_box['values'] = data


root = tk.Tk()
root.title("Relevant Listings")

# Text widget to display results
results_text = tk.Text(root, height=15, width=60, wrap=tk.WORD)  # Larger height and width, wrap by word
results_text.grid(row=5, column=0, columnspan=4)
results_text.bind("<Button-3>", on_right_click)

try:
    fetch_data()

    # Create combo boxes for selling and buying items
    sell_label = ttk.Label(root, text="Select item to sell:")
    sell_label.grid(row=0, column=0)
    sell_combo = ttk.Combobox(root, value=list(item_dict.values()))
    sell_combo.grid(row=0, column=1)
    sell_combo.bind('<KeyRelease>', sell_search)

    buy_label = ttk.Label(root, text="Select item to buy:")
    buy_label.grid(row=1, column=0)
    buy_combo = ttk.Combobox(root, value=list(item_dict.values()))
    buy_combo.grid(row=1, column=1)
    buy_combo.bind('<KeyRelease>', buy_search)

    # Label for last updated text
    last_update_label = ttk.Label(root, text="Last updated :")
    last_update_label.grid(row=3, column=2, columnspan=2)

    # Label for the last updated time
    lupdate_time_label = ttk.Label(root, text="")
    lupdate_time_label.grid(row=4, column=2, columnspan=2)

    # Checkbox for live search
    chk_state = tk.BooleanVar()
    live_search_checkbox = ttk.Checkbutton(root, text="Live Search", variable=chk_state, command=on_checkbox_clicked)
    live_search_checkbox.grid(row=0, column=2, columnspan=2)

    # Button to fetch relevant listings
    fetch_button = ttk.Button(root, text="Fetch Relevant Listings", command=filter_listings)
    fetch_button.grid(row=4, column=0, columnspan=2)

    # Button to refresh listings
    refresh_button = ttk.Button(root, text="Refresh Listings", command=fetch_and_update)
    refresh_button.grid(row=1, column=2, columnspan=2)

    update_time_label()

except Exception as e:
    results_text.insert(tk.END, "Unable to retrieve data from realmeye.com: " + str(e))

root.mainloop()
