import requests
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DataFetcher:
    """
    Handles all HTTP requests to the Liquipedia MediaWiki API for Rainbow Six Siege.
    """
    BASE_URL = "https://liquipedia.net/rainbowsix/api.php"
    USER_AGENT = "R6ProStats/0.1 (https://example.com/r6prostats; cooldev@example.com) PythonRequests"
    # Liquipedia asks for a 1 request per 2 seconds rate limit if not using a specific API key
    # For now, we'll be more conservative to be safe.
    REQUEST_INTERVAL = 2  # seconds

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.USER_AGENT})
        self.last_request_time = 0

    def _make_request(self, params: dict) -> dict:
        """
        Internal method to make a request to the API, respecting rate limits.
        """
        current_time = time.time()
        elapsed_time = current_time - self.last_request_time
        if elapsed_time < self.REQUEST_INTERVAL:
            sleep_time = self.REQUEST_INTERVAL - elapsed_time
            logging.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds.")
            time.sleep(sleep_time)

        try:
            response = self.session.get(self.BASE_URL, params=params)
            self.last_request_time = time.time()
            response.raise_for_status()  # Raise an exception for HTTP errors
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"API request failed: {e}")
            logging.error(f"Failed URL: {response.url if 'response' in locals() else self.BASE_URL + '?' + '&'.join([f'{k}={v}' for k, v in params.items()])}")
            # In a real app, might want to retry or handle more gracefully
            raise

    def get_page_content(self, page_title: str) -> str | None:
        """
        Retrieves the raw wikitext content of a single page.
        Returns the content as a string, or None if the page doesn't exist or an error occurs.
        """
        params = {
            "action": "query",
            "prop": "revisions",
            "titles": page_title,
            "rvprop": "content",
            "rvslots": "main", # Necessary to get content of main slot
            "format": "json",
            "formatversion": 2 # For simpler JSON structure
        }
        logging.info(f"Fetching content for page: {page_title}")
        try:
            data = self._make_request(params)
            page = data.get("query", {}).get("pages", [])[0] # formatversion=2 gives list of pages
            if page and not page.get("missing", False) and "revisions" in page:
                return page["revisions"][0]["slots"]["main"]["content"]
            elif page.get("missing", False):
                logging.warning(f"Page '{page_title}' not found.")
                return None
            else:
                logging.warning(f"Could not retrieve content for page '{page_title}'. Response: {data}")
                return None
        except Exception as e:
            logging.error(f"Error fetching page content for '{page_title}': {e}")
            return None

    def get_category_members(self, category_title: str, limit: int = 500) -> list[str]:
        """
        Retrieves a list of page titles belonging to a specific category.
        Note: MediaWiki API limits category member queries (default 500, max 5000 for bots).
        This function handles basic pagination up to 'limit'.
        """
        if not category_title.startswith("Category:"):
            category_title = f"Category:{category_title}"

        logging.info(f"Fetching members for category: {category_title}")
        members = []
        cmcontinue = None
        fetched_count = 0

        while fetched_count < limit:
            current_limit = min(500, limit - fetched_count) # Max 500 per API call for non-bots
            if current_limit <= 0:
                break

            params = {
                "action": "query",
                "list": "categorymembers",
                "cmtitle": category_title,
                "cmlimit": current_limit,
                "format": "json",
                "formatversion": 2
            }
            if cmcontinue:
                params["cmcontinue"] = cmcontinue

            try:
                data = self._make_request(params)
                if "query" in data and "categorymembers" in data["query"]:
                    current_batch = [page["title"] for page in data["query"]["categorymembers"]]
                    members.extend(current_batch)
                    fetched_count += len(current_batch)

                    if "continue" in data and "cmcontinue" in data["continue"]:
                        cmcontinue = data["continue"]["cmcontinue"]
                    else:
                        break # No more members
                else:
                    logging.warning(f"Could not retrieve members for category '{category_title}'. Response: {data}")
                    break
            except Exception as e:
                logging.error(f"Error fetching category members for '{category_title}': {e}")
                break

        logging.info(f"Found {len(members)} members in {category_title} (limit: {limit}).")
        return members

    def get_parsed_page_html(self, page_title: str) -> str | None:
        """
        Retrieves the parsed HTML content of a page.
        """
        params = {
            "action": "parse",
            "page": page_title,
            "prop": "text",
            "format": "json",
            "formatversion": 2
        }
        logging.info(f"Fetching parsed HTML for page: {page_title}")
        try:
            data = self._make_request(params)
            if "parse" in data and "text" in data["parse"]:
                return data["parse"]["text"]
            else:
                logging.warning(f"Could not retrieve parsed HTML for page '{page_title}'. Response: {data}")
                return None
        except Exception as e:
            logging.error(f"Error fetching parsed HTML for '{page_title}': {e}")
            return None

    def search_pages(self, search_term: str, limit: int = 10) -> list[str]:
        """
        Searches for pages using a search term. Returns a list of page titles.
        """
        params = {
            "action": "query",
            "list": "search",
            "srsearch": search_term,
            "srlimit": limit,
            "format": "json",
            "formatversion": 2
        }
        logging.info(f"Searching for pages with term: {search_term}")
        try:
            data = self._make_request(params)
            if "query" in data and "search" in data["query"]:
                return [result["title"] for result in data["query"]["search"]]
            else:
                logging.warning(f"Search for '{search_term}' yielded no results or an error. Response: {data}")
                return []
        except Exception as e:
            logging.error(f"Error searching pages for '{search_term}': {e}")
            return []

if __name__ == '__main__':
    # Example Usage (for testing purposes)
    fetcher = DataFetcher()

    # Test get_page_content
    page_title_to_test = "G2 Esports"
    print(f"\n--- Testing get_page_content for '{page_title_to_test}' ---")
    content = fetcher.get_page_content(page_title_to_test)
    if content:
        print(f"Successfully fetched content for {page_title_to_test}. Length: {len(content)}")
        # print(content[:500] + "...") # Print first 500 chars
    else:
        print(f"Failed to fetch content for {page_title_to_test}.")

    # Test get_page_content for a non-existent page
    non_existent_page = "ThisPageDoesNotExist12345"
    print(f"\n--- Testing get_page_content for non-existent page '{non_existent_page}' ---")
    content_ne = fetcher.get_page_content(non_existent_page)
    if not content_ne:
        print(f"Correctly handled non-existent page '{non_existent_page}'.")

    # Test get_category_members
    category_to_test = "Brazilian Teams" # A common category in R6 Liquipedia
    print(f"\n--- Testing get_category_members for '{category_to_test}' (limit 5) ---")
    members = fetcher.get_category_members(category_to_test, limit=5)
    if members:
        print(f"Found members in {category_to_test}: {members}")
    else:
        print(f"No members found or error for {category_to_test}.")

    # Test get_parsed_page_html
    page_for_html = "Operator" # A general page that should exist
    print(f"\n--- Testing get_parsed_page_html for '{page_for_html}' ---")
    html_content = fetcher.get_parsed_page_html(page_for_html)
    if html_content:
        print(f"Successfully fetched parsed HTML for {page_for_html}. Length: {len(html_content)}")
        # print(html_content[:500] + "...")
    else:
        print(f"Failed to fetch parsed HTML for {page_for_html}.")

    # Test search_pages
    search_term_to_test = "Six Invitational"
    print(f"\n--- Testing search_pages for '{search_term_to_test}' (limit 3) ---")
    search_results = fetcher.search_pages(search_term_to_test, limit=3)
    if search_results:
        print(f"Search results for '{search_term_to_test}': {search_results}")
    else:
        print(f"No search results for '{search_term_to_test}'.")

    # Example of fetching a specific tournament page
    # This is the kind of page whose content will need heavy parsing later
    tournament_page = "Six Invitational/2023"
    print(f"\n--- Fetching content for tournament page: '{tournament_page}' ---")
    tourn_content = fetcher.get_page_content(tournament_page)
    if tourn_content:
        print(f"Successfully fetched content for {tournament_page}. Length: {len(tourn_content)}")
        # This content will be full of wikitext templates like {{MatchMaps}}, {{MatchRecap}}, etc.
        # The WikitextParser module will be responsible for making sense of this.
    else:
        print(f"Failed to fetch content for {tournament_page}.")

    # Example of fetching an operator page
    operator_page = "Thermite"
    print(f"\n--- Fetching content for operator page: '{operator_page}' ---")
    op_content = fetcher.get_page_content(operator_page)
    if op_content:
        print(f"Successfully fetched content for {operator_page}. Length: {len(op_content)}")
    else:
        print(f"Failed to fetch content for {operator_page}.")

    # Example of fetching a map page
    map_page = "Oregon"
    print(f"\n--- Fetching content for map page: '{map_page}' ---")
    map_content = fetcher.get_page_content(map_page)
    if map_content:
        print(f"Successfully fetched content for {map_page}. Length: {len(map_content)}")
    else:
        print(f"Failed to fetch content for {map_page}.")

print("\nDataFetcher module implementation complete with basic functions and examples.")
