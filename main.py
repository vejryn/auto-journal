import argparse
import json
import csv
import sys
import gspread
import pprint
from time import sleep
from lib import bitmex
from setting import API_KEY, API_SECRET, API_BASE
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

pp = pprint.PrettyPrinter(indent=4)
scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('secret.json', scope)
client = gspread.authorize(creds)

sheet = client.open('Auto Journal') #Change this to spreadsheet name
worksheet = sheet.worksheet('Journal') #Change this to worksheet name

# Create connector
connector = bitmex.BitMEX(base_url=API_BASE, apiKey=API_KEY, apiSecret=API_SECRET)

# Do trade history query
count = 5 
query = {
    'reverse': 'true',
    'count': count
}

def retrieve():
    position = connector._curl_bitmex(path="position", verb="GET", timeout=10)
    history = connector._curl_bitmex(path="execution/tradeHistory", verb="GET", query=query, timeout=10)
    wallet = connector._curl_bitmex(path="user/walletHistory", verb="GET", query=query, timeout=10)
    data = worksheet.get_all_records()

    try:
        status_cell = worksheet.findall("open")
    except gspread.CellNotFound:
        status_cell = 0

    open_symbol = []
    for status in range(len(status_cell)):
        open_symbol.append(worksheet.cell(status_cell[status].row, 2).value)

    def get_rows(symbol):
        for status in range(len(status_cell)):
            if symbol == worksheet.cell(status_cell[status].row, 2).value:
                rows = status_cell[status].row
            else:
                rows = 99
        return rows

    for i in range(len(position)):
        currentQty = position[i]['currentQty']
        entry = position[i]['avgEntryPrice']
        ## new trade
        if position[i]['isOpen'] == True and position[i]['symbol'] not in open_symbol:
            new_rows = len(data)+2
            no = len(data)+1
            symbol = position[i]['symbol']
            open_date = datetime.strptime(position[i]['timestamp'], '%Y-%m-%dT%H:%M:%S.%fZ').strftime('%Y/%m/%d')
            if position[i]['currentQty'] > 0:
                _position = 'LONG'
            else:
                _position = 'SHORT'
            worksheet.update_cell(new_rows, 1, no)
            worksheet.update_cell(new_rows, 2, symbol)
            worksheet.update_cell(new_rows, 3, open_date)
            worksheet.update_cell(new_rows, 5, _position)
            worksheet.update_cell(new_rows, 6, currentQty)
            worksheet.update_cell(new_rows, 7, entry)
            worksheet.update_cell(new_rows, 11, 'open')
            print("New trade is recorded")
        ## update trade
        if position[i]['isOpen'] == True and position[i]['symbol'] in open_symbol:
            rows = get_rows(position[i]['symbol'])
            worksheet.update_cell(rows, 6, currentQty)
            worksheet.update_cell(rows, 7, entry)
            print("%s position is updated" % position[i]['symbol'])
        ## close trade
        if position[i]['isOpen'] == False and position[i]['symbol'] in open_symbol:
            rows = get_rows(position[i]['symbol'])
            close_date = datetime.strptime(position[i]['timestamp'], '%Y-%m-%dT%H:%M:%S.%fZ').strftime('%Y/%m/%d')
            exit = history[0]['lastPx']
            returns = position[i]['prevRealisedPnl'] / 100000000
            final_balance = wallet[0]['walletBalance'] / 100000000
            worksheet.update_cell(rows, 4, close_date)
            worksheet.update_cell(rows, 8, exit)
            worksheet.update_cell(rows, 9, returns)
            worksheet.update_cell(rows, 10, final_balance)
            worksheet.update_cell(rows, 11, 'closed')
        else:
            print("No change in %s position" % position[i]['symbol'])

while True:
    retrieve()
    sleep(3)