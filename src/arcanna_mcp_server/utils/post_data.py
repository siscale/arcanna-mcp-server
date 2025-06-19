import aiohttp


async def post_data(url, req_headers, data):
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=req_headers, json=data) as server_response:
            return await server_response.json()
