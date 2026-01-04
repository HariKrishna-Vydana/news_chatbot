import httpx
from agents import function_tool
from utils.settings import settings


@function_tool
async def search_news(query: str) -> str:
    """Search for recent news articles on a topic.

    Args:
        query: The news topic to search for, e.g., 'latest tech news', 'stock market today'

    Returns:
        A formatted string with news search results
    """
    if not settings.google_search_api_key or not settings.google_search_engine_id:
        return "News search is not configured. Please provide your response based on your knowledge."

    base_url = "https://www.googleapis.com/customsearch/v1"

    async with httpx.AsyncClient() as client:
        params = {
            "key": settings.google_search_api_key,
            "cx": settings.google_search_engine_id,
            "q": query,
            "num": 5,
        }
        try:
            response = await client.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("items", []):
                results.append(
                    f"- {item.get('title')}: {item.get('snippet')}"
                )

            if results:
                return "Here are the latest news results:\n" + "\n".join(results)
            return "No news results found for this query."

        except httpx.HTTPError as e:
            return f"Failed to search news: {str(e)}"
