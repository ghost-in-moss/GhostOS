import arxiv
from abc import ABC, abstractmethod

__all__ = ['ArxivSearchLib', 'ArxivSearchLibImpl']


class ArxivSearchLib(ABC):
    """Search information from Arxiv.org. \
    Useful for when you need to answer questions about Physics, Mathematics, \
    Computer Science, Quantitative Biology, Quantitative Finance, Statistics, \
    Electrical Engineering, and Economics from scientific articles on arxiv.org.
    """

    @abstractmethod
    def get_arxiv_article_information(
            self,
            query: str,
            top_k: int = 3,
    ) -> dict:
        """
        :param query: the content of search query
        :param top_k: top k articles match the query
        :return:
        """
        pass


class ArxivSearchLibImpl(ArxivSearchLib):
    def __init__(self):
        self._client = arxiv.Client()

    def get_arxiv_article_information(
            self,
            query: str,
            top_k: int = 3,
    ) -> dict:
        search = arxiv.Search(
            query=query,
            max_results=top_k,
            sort_by=arxiv.SortCriterion.SubmittedDate
        )
        results = self._client.results(search)
        articles = {}

        for result in results:
            article_info = {
                'title': result.title,
                'summary': result.summary,
                'authors': [str(author) for author in result.authors],
                'published': result.published
            }
            articles[result.entry_id] = article_info

        return articles


if __name__ == '__main__':
    lib = ArxivSearchLibImpl()
    print(lib.get_arxiv_article_information("new articles about openai o1 model"))

"""
This file is the first code that ghostos generated for me by gpt-4o. 
I talk to ModuleEditThought, give it instruction to start code completion, 
and review the code generation then suggest it to modify result structure.

some issues:
1. module edit thought create two implementations instead of modifying one.
2. when thought using moss to output, it forget to say something to me. I need to add some prompt.
"""

# if __name__ == "__main__":
#     from ghostos.prototypes.console import demo_console_app
#     from ghostos.thoughts.module_editor import new_pymodule_editor_thought
#
#     demo_console_app.run_thought(
#         new_pymodule_editor_thought(__name__),
#         instruction="""
# I need you to implement the ArxivSearchLib interface.
#
# I found a example in the pypi homepage of arxiv:
#
# ```python
# import arxiv
#
# # Construct the default API client.
# client = arxiv.Client()
#
# # Search for the 10 most recent articles matching the keyword "quantum."
# search = arxiv.Search(
#   query = "quantum",
#   max_results = 10,
#   sort_by = arxiv.SortCriterion.SubmittedDate
# )
#
# results = client.results(search)
#
# # `results` is a generator; you can iterate over its elements one by one...
# for r in client.results(search):
#   print(r.title)
# # ...or exhaust it into a list. Careful: this is slow for large results sets.
# all_results = list(results)
# print([r.title for r in all_results])
#
# # For advanced query syntax documentation, see the arXiv API User Manual:
# # https://arxiv.org/help/api/user-manual#query_details
# search = arxiv.Search(query = "au:del_maestro AND ti:checkerboard")
# first_result = next(client.results(search))
# print(first_result)
#
# # Search for the paper with ID "1605.08386v1"
# search_by_id = arxiv.Search(id_list=["1605.08386v1"])
# # Reuse client to fetch the paper, then print its title.
# first_result = next(client.results(search))
# print(first_result.title)
# ```
#
# refer to this example and make a better implementation.
# """
#     )
