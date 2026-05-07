import aiohttp


async def get_data(url, req_headers):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=req_headers) as server_response:
            server_response.raise_for_status()
            return await server_response.json()
