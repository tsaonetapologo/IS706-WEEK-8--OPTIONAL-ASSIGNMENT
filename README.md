# Economics SQL Quiz

**GitHub repository:** https://github.com/tsaonetapologo/IS706-WEEK-8--OPTIONAL-ASSIGNMENT
**Week 8 RAG deployment:** https://is706-week-8--optional-assignment-sddpwaerbgvz3y9wvwsav3.streamlit.app

This project is a Streamlit SQL lab backed by a hosted Supabase PostgreSQL
database. Students create an account or sign in, ask an economics question in
natural language, and receive AI-generated SQL using retrieval-augmented
generation (RAG). They can edit and run the generated query against the live
`economic_indicators` table, see the result rows, and save their SQL. Each
question is worth 4 points, for 20 points total.

## What I did to complete this assignment

1. **Built the quiz.** I created a Streamlit economics SQL quiz with five
   questions worth 4 points each (20 total), covering sorting, filtering,
   aggregation, counting, and population thresholds.
2. **Set up the hosted database.** I created a Supabase project and ran
   [`schema.sql`](./schema.sql) in the SQL Editor. It created and seeded the
   `economic_indicators` table with 10 countries, the owner-only `quiz_saves`
   table, and the restricted `quiz_reader` role.
3. **Added authentication.** I enabled Supabase email sign-up so students can
   create an account, sign in, and save their own queries.
4. **Made the SQL runner safe.** I limited it to a single parsed `SELECT`,
   ran it as `quiz_reader` in a read-only transaction, and added a five-second
   timeout and a 500-row limit.
5. **Added RAG.** I stored the schema and quiz examples as documents,
   embedded them with OpenAI, and stored the vectors in ChromaDB. Each question
   retrieves similar documents, which `gpt-4o-mini` uses to generate SQL.
6. **Auto-ran and validated generated SQL.** I made the app run each generated
   query through the read-only runner and compare the result with the expected
   rows.
7. **Wrote tests.** I wrote 17 unit tests covering the quiz content, query
   safety, and RAG. I ran them and they all passed.
8. **Set up GitHub Actions.** I added `database-check.yml` and stored the
   Session pooler URI as the repository secret `SUPABASE_DATABASE_URL`. I ran
   the workflow and it passed.
9. **Deployed the app.** I deployed `app.py` on Streamlit Community Cloud and
   added my Supabase, OpenAI, and database settings as secrets, so none are
   committed to the repository.
10. **Fixed problems along the way.** I corrected my Supabase project URL after
    a sign-in error, then fixed a database password authentication failure in
    my Streamlit secret.
11. **Tested the live app.** I signed in, clicked **Generate SQL**, and
    confirmed that the retrieved sources, generated SQL, result table, and
    "Correct!" outcome all appear.
12. **Made the app public and added evidence.** I set the app to public,
    captured three screenshots (see [Screenshots](#screenshots)), and added them
    to the repository with this README.
13. **Cleaned up the repository.** I closed an unneeded draft pull request from
    Copilot and deleted its branch, because my corrected secret already fixed
    the failing database check.

## RAG architecture

1. The app stores the `economic_indicators` schema and the five quiz
   question/SQL examples as knowledge documents.
2. OpenAI's `text-embedding-3-small` turns these documents into vectors. The
   vectors are stored in a ChromaDB in-memory collection, initialized once per
   app process.
3. For each natural-language question, the app embeds the question and performs
   a similarity search in ChromaDB. It sends the retrieved documents to OpenAI's
   `gpt-4o-mini` model, which returns a PostgreSQL `SELECT` query.
4. The retrieved sources and generated SQL are shown in the quiz. The SQL is
   placed in the existing editor and automatically passed through the existing
   PostgreSQL runner, which only permits one read-only `SELECT`.
5. The result table is displayed and compared with that quiz question's
   expected rows. Users can still edit and run SQL manually.

The vector search is performed against ChromaDB; schema and examples are not
simply added to the prompt without retrieval.

## Student quiz instructions

1. Create an account or sign in.
2. Choose a question and write a SQL query.
3. Select **Run query** to execute your SQL manually and see the live result.
4. Review the result, edit your query, and run it again as often as you need.
5. For AI assistance, enter a natural-language question and select
   **Generate SQL**. The app retrieves relevant context, generates SQL, runs it
   using the read-only quiz role, displays the result table, and reports whether
   the result matches the expected answer. Review and edit the SQL in the
   existing editor as needed.

Each question's hint expander contains both the expected SQL and expected result
from the start. Query attempts are unlimited. Use the **Dark mode** toggle in
the sidebar to switch to a dark background.

## Stack and access controls

- **Hosted database and authentication:** Supabase PostgreSQL and Supabase Auth.
- **Web app:** Streamlit.
- **Database driver:** psycopg connects through Supabase's **Session pooler**
  using TLS (`sslmode=require`).
- **GitHub Actions:** `.github/workflows/database-check.yml` verifies that the
  hosted table can be queried using a repository secret.
- Only signed-in users can run or save queries. Supabase row-level security
  restricts saved queries to their owner.
- The SQL runner accepts exactly one parsed `SELECT`, switches to the
  `quiz_reader` database role, opens a read-only transaction, applies a
  five-second timeout, and limits displayed results to 500 rows.

## Supabase setup

1. Create a Supabase project. In **Authentication → Providers**, enable email
   sign-up. For a classroom deployment, either configure email delivery so
   students can confirm accounts or disable email confirmation for the class.
2. In **Project Settings → API**, copy the project URL and its publishable key
   (or legacy anon key). The app uses this key for Supabase Auth and the
   row-level-security-protected `quiz_saves` table. Do not use a service-role
   key in the app.
3. In the Supabase SQL Editor, run [`schema.sql`](./schema.sql). It creates and
   seeds the economics table, creates the private save table and its
   owner-only policy, and configures the restricted query role. The supplied
   data contains 10 countries.
4. In **Database → Connect**, select the **Session pooler** (not Direct
   connection) and copy its PostgreSQL URI. Put the database password in that
   URI and ensure it has `sslmode=require`. The connection must be able to
   `SET ROLE quiz_reader`; the setup SQL grants that membership to the
   Supabase `postgres` login.

## Run locally

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env` with the Supabase project URL, publishable/anon key, Session
pooler database URI, and OpenAI API key:

```dotenv
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_KEY=your-publishable-or-anon-key
OPENAI_API_KEY=your-openai-api-key
SUPABASE_DATABASE_URL=postgresql://postgres.your-project-ref:YOUR_DB_PASSWORD@POOLER_HOST:5432/postgres?sslmode=require
```

Keep `.env` private; `.gitignore` excludes it. The OpenAI API key is required
for SQL generation. Start the app:

```sh
streamlit run app.py
```

Open the local URL printed by Streamlit, create an account or sign in, choose a
question, and try **Generate SQL** or write a query yourself. Generated SQL is
automatically executed with read-only access. **Save query** stores that
question's SQL under the signed-in user's account. Follow the
[student quiz instructions](#student-quiz-instructions) for the unlimited
attempts and hint details.

Run the local test suite with:

```sh
python -m unittest discover -s tests -v
```

## GitHub Actions

1. Push this project to a GitHub repository.
2. In **Settings → Secrets and variables → Actions**, add a repository secret
   named `SUPABASE_DATABASE_URL`. Its value is the same Session pooler URI used
   locally, with `sslmode=require`. Do not put the password in workflow YAML,
   source files, or commit history.
3. Push a commit or use **Actions → Hosted database check → Run workflow**.
   A successful job reports that the connection and `quiz_reader` access work.

The workflow deliberately tests with the restricted `quiz_reader` role, not
with a superuser query path.

## Deploy the quiz site

1. Sign in to Streamlit Community Cloud and create an app from
   `tsaonetapologo/IS706-WEEK-8--OPTIONAL-ASSIGNMENT`, selecting `app.py` as the
   entry point.
2. In the app's **Settings → Secrets**, add the four settings in TOML form:

   ```toml
   SUPABASE_URL = "https://your-project-ref.supabase.co"
   SUPABASE_KEY = "your-publishable-or-anon-key"
   OPENAI_API_KEY = "your-openai-api-key"
   SUPABASE_DATABASE_URL = "postgresql://postgres.your-project-ref:YOUR_DB_PASSWORD@POOLER_HOST:5432/postgres?sslmode=require"
   ```

3. Wait for the app to deploy and test the full question → retrieved sources →
   generated SQL → result workflow. The live app is deployed at the URL at the
   top of this README. Deployment requires valid Supabase settings and an
   OpenAI API key; these are not committed to this repository.

## Screenshots

Screenshots of the deployed app:

1. The quiz question.
   ![Economics SQL Quiz question](docs/screenshot-1.png)
2. The natural-language question, generated SQL, and retrieved ChromaDB sources.
   ![Generated SQL with retrieved sources](docs/screenshot-2.png)
3. The executed generated SQL, result table, and "Correct!" validation outcome.
   ![Result table and validation outcome](docs/screenshot-3.png)

## Quiz questions

All questions require writing SQL; none are multiple choice. They cover
sorting, filtering, aggregation, counting, and population thresholds. Students
can compare their result with the expected rows and see the example SQL in each
question's hint from the start. Students may submit unlimited query attempts;
see [student quiz instructions](#student-quiz-instructions) for the full process.
