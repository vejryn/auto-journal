import argparse
import json
import csv
import sys
import gspread
import pprint
from time import sleep
from lib import bitmex
from settings_ import API_KEY, API_SECRET, API_BASE
from oauth2client.service_account import ServiceAccountCredentials

pp = pprint.PrettyPrinter(indent=4)
scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('secret.json', scope)
client = gspread.authorize(creds)

# Create connector
connector = bitmex.BitMEX(base_url=API_BASE, apiKey=API_KEY, apiSecret=API_SECRET)

# Do trade history query
count = 5  # max API will allow
query = {
    'reverse': 'true',
    'count': count
}

while True:
    pos = []
    #gpsread
    sheet = client.open('Capital Preservation').sheet1
    data = sheet.get_all_records()
    last = len(data)+1
    newrow = last+1
    status = str(sheet.cell(newrow,10).value)
    lastExitSheet = str(sheet.cell(last,10).value)
    sheetqty = str(sheet.cell(last,5).value)
    sheetentry = str(sheet.cell(last,6).value)

    #bitmex api
    position = connector._curl_bitmex(path="position", verb="GET", timeout=10)
    pos.extend(position)
    XBT = pos[1]
    pp.pprint("Connected - Fetching Position")
    pp.pprint("Current Quantity : %s" % XBT["currentQty"])
    pp.pprint("Current Avg. Entry : %s" % XBT["avgEntryPrice"])
    
    if XBT["isOpen"] == True and XBT["symbol"] == "XBTUSD" and lastExitSheet == "closed":
        sheet.update_cell(newrow,1,newrow) #nomer
        sheet.update_cell(newrow,2,XBT["openingTimestamp"][slice(10)]) #open timestamp
        sheet.update_cell(newrow,6,XBT["avgEntryPrice"]) #avg entry
        if XBT["bankruptPrice"] < XBT["avgEntryPrice"]:
            sheet.update_cell(newrow,4,"LONG")
            sheet.update_cell(newrow,5,XBT["currentQty"]) #opening quantity long
        else:
            sheet.update_cell(newrow,4,"SHORT")
            sheet.update_cell(newrow,5,"-"+XBT["currentQty"]) #opening quantity short

    elif XBT["isOpen"] == True and XBT["symbol"] == "XBTUSD" and sheetqty != str(XBT["currentQty"]):
        sheet.update_cell(last,6,XBT["avgEntryPrice"]) #update avg entry
        if XBT["bankruptPrice"] < XBT["avgEntryPrice"]:
            sheet.update_cell(last,5,XBT["currentQty"]) #update qty long
        else:
            sheet.update_cell(last,5,"-"+XBT["currentQty"]) #update qty short
        sheetqty = str(XBT["currentQty"])
        pp.pprint("Updated Quantity : %s" % sheetqty)
        pp.pprint("Updated Avg. Entry : %s" % sheetentry)

    if XBT["isOpen"] == False and XBT["symbol"] == "XBTUSD" and lastExitSheet != "closed":
        out = []
        data = connector._curl_bitmex(path="execution/tradeHistory", verb="GET", query=query, timeout=10)
        out.extend(data)
        
        for x in out:
            if x["ordStatus"] == "Filled":
                if x["execType"] == "Trade":
                    if x["symbol"] == "XBTUSD":
                        if "Close" in x["execInst"]:
                            pp.pprint(x["avgPx"])
                            sheet.update_cell(last,7,XBT["prevRealisedPnl"])
                            sheet.update_cell(last,8,"closed")
                            sheet.update_cell(last,3,x["timestamp"][slice(10)])
                            sheet.update_cell(last,10,"closed")
    sleep(3)

    