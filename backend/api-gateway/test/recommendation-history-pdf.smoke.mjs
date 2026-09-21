const BASE_URL = process.env.TALENTFLOW_E2E_BASE_URL || "http://127.0.0.1:3000";
const GRAPHQL_URL = process.env.TALENTFLOW_E2E_GRAPHQL_URL || `${BASE_URL}/graphql`;

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function randomSuffix() {
  return Math.random().toString(36).slice(2, 10);
}

async function postJson(url, body, headers = {}) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
    body: JSON.stringify(body),
  });
  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  return { response, data };
}

async function run() {
  const email = `smoke_${randomSuffix()}@example.com`;
  const password = process.env.SMOKE_TEST_PASSWORD || "";

  const register = await postJson(`${BASE_URL}/auth/register`, {
    email,
    password,
    name: "Smoke Test User",
  });
  assert(register.response.ok, `Register failed: ${register.response.status} ${JSON.stringify(register.data)}`);
  assert(register.data?.access_token, "Register response missing access_token");
  const token = register.data.access_token;

  const recommendMutation = `
    mutation Recommend($input: RecommendCvTextInput!) {
      recommendFromCvText(input: $input) {
        queryUsed
        totalResults
        assistantMessage
        llmUsed
        llmProvider
        llmModel
        llmError
        llmStatus
        cvAnalysis {
          skills
          experienceYears
          educationLevel
          rawTextPreview
        }
        jobs {
          id
          title
          company
          location
          contractType
          sourceName
          sourceUrl
          postedDate
          score
          summary
        }
        assistantStructured {
          mode
          profileSummary
          strengths
          gaps
          actions
          reasonIfNoMatch
          recommendedJobs {
            jobId
            title
            why
            url
            cvImprovement
          }
        }
        atsLite {
          overallScore
          structureScore
          alignmentScore
          evidenceScore
          readinessLabel
          summary
          matchedKeywords
          missingKeywords
          suggestions
          actionPlan
        }
      }
    }
  `;

  const cvText =
    "Ingenieur data et IA avec 5 ans d'experience en Python, FastAPI, Spark, Kafka, Docker, PostgreSQL, NLP et recommandation. " +
    "A deja deploie des APIs et optimise des pipelines de matching. Marqueur smoke: TF-E2E-20260403.";

  const recommend = await postJson(
    GRAPHQL_URL,
    {
      query: recommendMutation,
      variables: {
        input: {
          cvText,
          topK: 5,
        },
      },
    },
    {
      Authorization: `Bearer ${token}`,
    },
  );

  assert(recommend.response.ok, `Recommend failed: ${recommend.response.status} ${JSON.stringify(recommend.data)}`);
  assert(!recommend.data?.errors, `Recommend GraphQL errors: ${JSON.stringify(recommend.data.errors)}`);
  const recommendation = recommend.data?.data?.recommendFromCvText;
  assert(recommendation, "Missing recommendFromCvText payload");
  assert(Array.isArray(recommendation.jobs), "Recommendation jobs missing");
  assert(recommendation.assistantStructured, "assistantStructured missing");
  assert(
    recommendation.jobs.length > 0 || recommendation.assistantStructured?.mode === "no_match",
    "Recommendation returned neither jobs nor a valid no_match decision",
  );

  const saveMutation = `
    mutation SaveHistory($input: SaveRecommendationHistoryInput!) {
      saveRecommendationHistory(input: $input) {
        id
        totalResults
        llmStatus
        assistantStructured {
          mode
        }
      }
    }
  `;

  const saveInput = {
    cvTextPreview: cvText.slice(0, 180),
    fileName: "smoke-test-cv.txt",
    queryUsed: recommendation.queryUsed,
    assistantMessage: recommendation.assistantMessage,
    llmUsed: recommendation.llmUsed,
    llmProvider: recommendation.llmProvider,
    llmModel: recommendation.llmModel,
    llmError: recommendation.llmError,
    llmStatus: recommendation.llmStatus,
    totalResults: recommendation.totalResults,
    assistantStructured: recommendation.assistantStructured,
    cvAnalysis: recommendation.cvAnalysis,
    atsLite: recommendation.atsLite,
    jobs: recommendation.jobs,
  };

  const save = await postJson(
    GRAPHQL_URL,
    {
      query: saveMutation,
      variables: { input: saveInput },
    },
    {
      Authorization: `Bearer ${token}`,
    },
  );

  assert(save.response.ok, `Save history failed: ${save.response.status} ${JSON.stringify(save.data)}`);
  assert(!save.data?.errors, `Save history GraphQL errors: ${JSON.stringify(save.data.errors)}`);
  const historyId = save.data?.data?.saveRecommendationHistory?.id;
  assert(historyId, "History id missing after saveRecommendationHistory");

  const pdfResponse = await fetch(`${BASE_URL}/reports/history/${historyId}.pdf`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const pdfBytes = new Uint8Array(await pdfResponse.arrayBuffer());

  assert(pdfResponse.ok, `PDF download failed: ${pdfResponse.status}`);
  assert((pdfResponse.headers.get("content-type") || "").includes("application/pdf"), "PDF content-type invalid");
  assert(pdfBytes.byteLength > 5000, `PDF payload too small: ${pdfBytes.byteLength} bytes`);

  console.log(
    JSON.stringify(
      {
        ok: true,
        email,
        llmStatus: recommendation.llmStatus,
        llmProvider: recommendation.llmProvider,
        mode: recommendation.assistantStructured?.mode,
        totalResults: recommendation.totalResults,
        historyId,
        pdfBytes: pdfBytes.byteLength,
      },
      null,
      2,
    ),
  );
}

run().catch((error) => {
  console.error(JSON.stringify({ ok: false, error: String(error?.message || error) }, null, 2));
  process.exit(1);
});
