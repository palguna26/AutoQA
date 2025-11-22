AutoQA is an github application which will revolutionize the way AI can be used in Quality assurance.

What it does:-
1. Generates Issue check list and stores it in a postgre SQL DB in render whenever an issue is raised in a repo.
2. When a pull request is open it automatically reviews the code in the branch against the issue checklist which was created.
3. It does so by creating unit test cases as described per requirement in the issue checklist.
4. after all this it creates a documentaion/ report which gets stored in the db so that the project leads can just read it and then decide to merge the PR.

Tech Stack:-
Backend:-Python + FastApi, Render(For Webhook and Postgre)
DB:-Postgre
LLM:- Groq Key
Github integrated app.