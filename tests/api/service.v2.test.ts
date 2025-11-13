import axios from "axios";

function baseUrl() {
  const b = (process.env.DJANGO_BASE_URL || "").replace(/\/+$/, "");
  if (!b) throw new Error("DJANGO_BASE_URL is required");
  return b;
}

// Allow overrides, but defaults match your Django routes.
const V2_SEARCH_PATH = process.env.SERVICE_V2_SEARCH_PATH || "/v2/services";
const V2_DETAIL_PATH = process.env.SERVICE_V2_DETAIL_PATH || "/v2/service";

const asArray = (data: any): any[] =>
  Array.isArray(data) ? data : (Array.isArray(data?.results) ? data.results : []);

describe("Service v2", () => {
  it("POST /v2/services -> 200 and data array", async () => {
    // minimal body {} should return all (paginated window) per your spec
    const res = await axios.post(`${baseUrl()}${V2_SEARCH_PATH}`, {}, { validateStatus: () => true });
    expect(res.status).toBe(200);

    const list = asArray(res.data);
    expect(Array.isArray(list)).toBe(true);

    if (list.length) {
      expect(list[0]).toHaveProperty("id");
      expect(
        "serviceName" in list[0] || "name" in list[0]
      ).toBe(true);
    }
  });

  it("GET /v2/service/{id} -> 200 and object", async () => {
    // obtain an id from the search endpoint
    const seed = await axios.post(`${baseUrl()}${V2_SEARCH_PATH}`, {}, { validateStatus: () => true });
    expect(seed.status).toBe(200);
    const list = asArray(seed.data);
    if (!list.length) return;

    const id = list[0].id;
    const res = await axios.get(`${baseUrl()}${V2_DETAIL_PATH}/${id}`, { validateStatus: () => true });
    expect(res.status).toBe(200);
    expect(res.headers["content-type"] || "").toMatch(/application\/json/i);
    expect(res.data).toHaveProperty("id", id);
    expect(
      "serviceName" in res.data || "name" in res.data
    ).toBe(true);
    expect(res.data).toHaveProperty("description");
  });
});
