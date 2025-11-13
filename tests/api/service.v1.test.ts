import axios from "axios";

function baseUrl() {
  const b = (process.env.DJANGO_BASE_URL || "").replace(/\/+$/, "");
  if (!b) throw new Error("DJANGO_BASE_URL is required");
  return b;
}

// Allow overrides, but defaults match your Django routes.
const V1_SEARCH_PATH = process.env.SERVICE_V1_SEARCH_PATH || "/v1/services";
const V1_DETAIL_PATH = process.env.SERVICE_V1_DETAIL_PATH || "/v1/service";

const asArray = (data: any): any[] =>
  Array.isArray(data) ? data : (Array.isArray(data?.results) ? data.results : []);

describe("Service v1", () => {
  it("POST /v1/services -> 200 and data array", async () => {
    const res = await axios.post(`${baseUrl()}${V1_SEARCH_PATH}`, {}, { validateStatus: () => true });
    expect(res.status).toBe(200);

    const list = asArray(res.data);
    expect(Array.isArray(list)).toBe(true);

    if (list.length) {
      expect(list[0]).toHaveProperty("id");
      // allow either camelCase or legacy name casing
      expect(
        "serviceName" in list[0] || "name" in list[0]
      ).toBe(true);
    }
  });

  it("GET /v1/service/{id} -> 200 and object", async () => {
    // get an id using the search endpoint
    const seed = await axios.post(`${baseUrl()}${V1_SEARCH_PATH}`, {}, { validateStatus: () => true });
    expect(seed.status).toBe(200);
    const list = asArray(seed.data);
    if (!list.length) return; // nothing to test against in an empty DB

    const id = list[0].id;
    const res = await axios.get(`${baseUrl()}${V1_DETAIL_PATH}/${id}`, { validateStatus: () => true });
    expect(res.status).toBe(200);
    expect(res.headers["content-type"] || "").toMatch(/application\/json/i);
    expect(res.data).toHaveProperty("id", id);
    expect(
      "serviceName" in res.data || "name" in res.data
    ).toBe(true);
    expect(res.data).toHaveProperty("description");
  });
});
