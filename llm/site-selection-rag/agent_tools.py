# import json
# from google import genai
# from google.genai import types

# # import vertexai
# # from vertexai.generative_models import FunctionDeclaration, Tool, Part

# # Specify a function declaration and parameters for an API request
# get_papers_by_category_func = types.FunctionDeclaration(
#     name="get_papers_by_category",
#     description="Get research paper chunks filtered by category (topic area)",
#     # Function parameters are specified in OpenAPI JSON schema format
#     parameters={
#         "type": "object",
#         "properties": {
#             "category": {
#                 "type": "string",
#                 "description": "The paper category/topic area",
#                 "enum": [
#                     "land value",
#                     "zoning urban planning",
#                     "land",
#                     "general",
#                 ],
#             },
#             "search_content": {
#                 "type": "string",
#                 "description": "The search text to filter content from research papers. The search term is compared against the paper text based on cosine similarity. Expand the search term to a sentence or two to get better matches",
#             },
#         },
#         "required": ["category", "search_content"],
#     },
# )


# def get_papers_by_category(category, search_content, collection, embed_func):

#     query_embedding = embed_func(search_content)

#     # Query based on embedding value
#     results = collection.query(
#         query_embeddings=[query_embedding], n_results=10, where={"category": category}
#     )
#     return "\n".join(results["documents"][0])


# get_papers_by_search_content_func = types.FunctionDeclaration(
#     name="get_papers_by_search_content",
#     description="Get research paper chunks filtered by search terms across all categories",
#     # Function parameters are specified in OpenAPI JSON schema format
#     parameters={
#         "type": "object",
#         "properties": {
#             "search_content": {
#                 "type": "string",
#                 "description": "The search text to filter content from research papers. The search term is compared against the paper text based on cosine similarity. Expand the search term to a sentence or two to get better matches",
#             },
#         },
#         "required": ["search_content"],
#     },
# )


# def get_papers_by_search_content(search_content, collection, embed_func):

#     query_embedding = embed_func(search_content)

#     # Query based on embedding value
#     results = collection.query(query_embeddings=[query_embedding], n_results=10)
#     return "\n".join(results["documents"][0])


# # Define all functions available to the real estate expert
# real_estate_expert_tool = types.Tool(
#     function_declarations=[get_papers_by_category_func, get_papers_by_search_content_func]
# )


# def execute_function_calls(function_calls, collection, embed_func):
#     parts = []
#     for function_call in function_calls:
#         print("Function:", function_call.name)
#         if function_call.name == "get_papers_by_category":
#             print(
#                 "Calling function with args:",
#                 function_call.args["category"],
#                 function_call.args["search_content"],
#             )
#             response = get_papers_by_category(
#                 function_call.args["category"],
#                 function_call.args["search_content"],
#                 collection,
#                 embed_func,
#             )
#             print("Response:", response)
#             # function_responses.append({"function_name":function_call.name, "response": response})
#             parts.append(
#                 types.Part.from_function_response(
#                     name=function_call.name,
#                     response={
#                         "content": response,
#                     },
#                 ),
#             )
#         if function_call.name == "get_papers_by_search_content":
#             print("Calling function with args:", function_call.args["search_content"])
#             response = get_papers_by_search_content(
#                 function_call.args["search_content"], collection, embed_func
#             )
#             print("Response:", response)
#             # function_responses.append({"function_name":function_call.name, "response": response})
#             parts.append(
#                 types.Part.from_function_response(
#                     name=function_call.name,
#                     response={
#                         "content": response,
#                     },
#                 ),
#             )

#     return parts
