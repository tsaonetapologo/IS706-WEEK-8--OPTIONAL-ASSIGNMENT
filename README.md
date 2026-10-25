# Economics SQL Quiz

**GitHub repository:** https://github.com/tsaonetapologo/IS706-WEEK-8--OPTIONAL-ASSIGNMENT
**Current quiz deployment (redeploy this RAG version):** https://ids706-week7-assignment--economics-sql-quiz-cdqjbyzzrxtpiyyepq.streamlit.app/

This project is a Streamlit SQL lab backed by a hosted Supabase PostgreSQL
database. Students create an account or sign in, ask an economics question in
natural language, and receive AI-generated SQL using retrieval-augmented
generation (RAG). They can edit and run the generated query against the live
`economic_indicators` table, see the result rows, and save their SQL. Each
question is worth 4 points, for 20 points total.

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
   placed in the existing editor; it is not run automatically. The existing
   PostgreSQL runner still restricts execution to one read-only `SELECT`.

The vector search is performed against ChromaDB; schema and examples are not
simply added to the prompt without retrieval.

## Student quiz instructions

1. Create an account or sign in.
2. Choose a question and write a SQL query.
3. Select **Run query** to execute your SQL and see the live result.
4. Review the result, edit your query, and run it again as often as you need.
5. For AI assistance, enter a natural-language question and select
   **Generate SQL**. Review the retrieved sources and generated query, then run
   it from the SQL editor if you choose.

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
not executed until you select **Run query**. **Save query** stores that
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

1. Push the project to GitHub and sign in to Streamlit Community Cloud.
2. Create an app from the repository, selecting `app.py` as the entry point.
3. In the app's **Settings → Secrets**, add the four settings in TOML form:

   ```toml
   SUPABASE_URL = "https://your-project-ref.supabase.co"
   SUPABASE_KEY = "your-publishable-or-anon-key"
   OPENAI_API_KEY = "your-openai-api-key"
   SUPABASE_DATABASE_URL = "postgresql://postgres.your-project-ref:YOUR_DB_PASSWORD@POOLER_HOST:5432/postgres?sslmode=require"
   ```

4. After the RAG version deploys, update the deployment link at the top of this
   README if its URL changes. Verify generation with a sample question and add a
   screenshot showing the question and generated SQL. Submit the GitHub
   repository URL.

## Screenshots

After deploying and configuring `OPENAI_API_KEY`, capture the app with a
question and its generated SQL, and add that image here before submission.

## Quiz questions

All questions require writing SQL; none are multiple choice. They cover
sorting, filtering, aggregation, counting, and population thresholds. Students
can compare their result with the expected rows and see the example SQL in each
question's hint from the start. Students may submit unlimited query attempts;
see [student quiz instructions](#student-quiz-instructions) for the full process.
