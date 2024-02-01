import abc
import typing

__all__ = ["QueryFormatter", "SortFormatter"]


class BaseFormatter(abc.ABC):
    @abc.abstractmethod
    def format(self, **params) -> typing.Optional[typing.Sequence]: ...


class QueryFormatter(BaseFormatter):
    @staticmethod
    def _get_search_query(params) -> dict:
        search = {
            "match": {
                params[0]: {"query": params[1], "fuzziness": "auto"},
            }
        }
        return search

    @staticmethod
    def _get_filter_query(filter_param) -> dict:
        filter_res = {
            "nested": {
                "path": "genre",
                "query": {
                    "term": {"genre.id": str(filter_param)},
                },
            },
        }
        return filter_res

    def format(self, **params) -> typing.Optional[dict]:
        query = {
            "bool": {"must": []},
        }
        if params.get("search_query"):
            query["bool"]["must"].append(self._get_search_query(params.get("search_query")))
        if params.get("genre_uuid"):
            query["bool"]["must"].append(self._get_filter_query(params.get("genre_uuid")))
        return query if query["bool"]["must"] else None


class SortFormatter(BaseFormatter):
    @staticmethod
    def _get_sort_query(sort_param) -> tuple:
        return ({sort_param[1:]: "desc"} if sort_param.startswith("-") else {sort_param: "asc"},)

    def format(self, **params) -> typing.Optional[tuple]:
        if params.get("sort"):
            return self._get_sort_query(params.get("sort"))
        else:
            return {"_score": "desc"}, {"id": "asc"}
