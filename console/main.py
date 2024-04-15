import aiohttp
import asyncio
from datetime import datetime, timedelta
import json
import logging
import platform
import sys

logger = logging.getLogger()
stream_handler = logging.StreamHandler()
logger.addHandler(stream_handler)
logger.setLevel(logging.INFO)


class HttpError(Exception):
	pass


def json_format(data, value=None):
	view_currency = ['EUR', 'USD']
	if value:
		view_currency.append(value)
	output_list = []
	for daily_data in data:
		date = daily_data['date']
		entry = {date: {}}
		for rate in daily_data['exchangeRate']:
			if rate['currency'] in view_currency:
				currency_json = rate['currency']
				entry[date][currency_json] = {
					'sale': rate.get('saleRate', rate['saleRateNB']),
					'purchase': rate.get('purchaseRate', rate['purchaseRateNB'])
				}
		output_list.append(entry)
	json_string = json.dumps(output_list, indent=2, ensure_ascii=False)
	return json_string


async def main(data_index):
	try:
		response = await request(f'https://api.privatbank.ua/p24api/exchange_rates?date={data_index}')
		return response
	except HttpError as err:
		logging.info(err)
		return None


async def request(url: str):
	async with aiohttp.ClientSession() as session:
		try:
			async with session.get(url) as resp:
				if resp.status == 200:
					result_request = await resp.json()
					return result_request
				else:
					raise HttpError(f"Error status: {resp.status} for {url}")
		except (aiohttp.ClientConnectorError, aiohttp.InvalidURL) as err:
			raise HttpError(f'Connection error: {url}', str(err))


if __name__ == '__main__':
	currency = []
	if platform.system() == 'Windows':
		asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
	if len(sys.argv) < 2 or len(sys.argv) > 3:
		raise 'Error enter data'
	request_day = sys.argv[1]
	# stat_time = time()
	if request_day.isdigit() and int(request_day) <= 10:
		start_date = datetime.now() - timedelta(days=int(request_day) - 1)
		end_date = datetime.now()

		while start_date <= end_date:
			result = asyncio.run(main(start_date.strftime("%d.%m.%Y")))
			if result:
				currency.append(result)
			start_date += timedelta(days=1)
	else:
		raise 'The request must be no more than 10 days!'
	if len(sys.argv) == 2:
		logging.info(json_format(currency))
	else:
		value_response = str(sys.argv[2]).upper()
		logging.info(json_format(currency, value_response))
