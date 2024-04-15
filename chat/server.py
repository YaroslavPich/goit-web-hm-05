from datetime import datetime, timedelta
import json
import logging

import aiofile
from aiopath import AsyncPath
import asyncio
import httpx
import websockets
import names
from websockets import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosedOK

logging.basicConfig(level=logging.INFO)

async def log_exchange():
	async with aiofile.AIOFile('exchange_log.txt', 'a') as file:
		await file.write(f'{datetime.now()} - exchange command.')


async def request(url: str):
	async with httpx.AsyncClient(timeout=130) as client:
		r = await client.get(url)
		if r.status_code == 200:
			result = r.json()
			return result
		else:
			return None


def json_format(data=None):
	view_currency = ['EUR', 'USD']
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


async def get_exchange(currency_date=None):
	if currency_date is None:
		currency_date = datetime.now().strftime("%d.%m.%Y")
	response = await request(f'https://api.privatbank.ua/p24api/exchange_rates?date={currency_date}')
	return response


async def days_currency(index_days):
	currency = []
	start_date = datetime.now() - timedelta(days=index_days - 1)
	end_date = datetime.now()
	while start_date <= end_date:
		result = await get_exchange(start_date.strftime("%d.%m.%Y"))
		if result:
			currency.append(result)
		start_date += timedelta(days=1)
	return currency


class Server:
	clients = set()

	async def register(self, ws: WebSocketServerProtocol):
		ws.name = names.get_full_name()
		self.clients.add(ws)
		logging.info(f'{ws.remote_address} connects')

	async def unregister(self, ws: WebSocketServerProtocol):
		self.clients.remove(ws)
		logging.info(f'{ws.remote_address} disconnects')

	async def send_to_clients(self, message: str):
		if self.clients:
			[await client.send(message) for client in self.clients]

	async def ws_handler(self, ws: WebSocketServerProtocol):
		await self.register(ws)
		try:
			await self.distribute(ws)
		except ConnectionClosedOK:
			pass
		finally:
			await self.unregister(ws)

	async def distribute(self, ws: WebSocketServerProtocol):
		async for message in ws:
			parts = message.split()
			if len(parts) == 2 and parts[0] == 'exchange' and parts[1].isdigit() and int(parts[1]) <= 10:
				await log_exchange()
				exchange = await days_currency(int(parts[1]))
				await self.send_to_clients(json_format(exchange))
			elif message == 'exchange':
				await log_exchange()
				exchange = await get_exchange()
				await self.send_to_clients(json_format([exchange]))
			elif message == 'Hello server':
				await self.send_to_clients('Hello all')
			else:
				await self.send_to_clients(f"{ws.name}: {message}")


async def main():
	server = Server()
	async with websockets.serve(server.ws_handler, 'localhost', 8080):
		await asyncio.Future()


if __name__ == '__main__':
	asyncio.run(main())
