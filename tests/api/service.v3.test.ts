import axios from "axios";

function baseUrl() {
  const b = (process.env.DJANGO_BASE_URL || "").replace(/\/+$/, "");
  if (!b) throw new Error("DJANGO_BASE_URL is required");
  return b;
}

const V3_SEARCH_PATH = process.env.SERVICE_V3_SEARCH_PATH || "/v3/services";
const V3_DETAIL_PATH = process.env.SERVICE_V3_DETAIL_PATH || "/v3/service";

const asArray = (data: any): any[] =>
  Array.isArray(data) ? data : (Array.isArray(data?.results) ? data.results : []);

describe("Service v3", () => {
  it("POST /v3/services -> 200 and data array", async () => {
    const res = await axios.post(`${baseUrl()}${V3_SEARCH_PATH}`, {}, { validateStatus: () => true });
    expect(res.status).toBe(200);

    const list = asArray(res.data);
    expect(Array.isArray(list)).toBe(true);

    if (list.length) {
      expect(list[0]).toHaveProperty("id");
      expect("serviceName" in list[0] || "name" in list[0]).toBe(true);
    }
  });

  it("GET /v3/service/{id} -> 200 and object", async () => {
    const seed = await axios.post(`${baseUrl()}${V3_SEARCH_PATH}`, {}, { validateStatus: () => true });
    expect(seed.status).toBe(200);
    const list = asArray(seed.data);
    if (!list.length) return;

    const id = list[0].id;
    const res = await axios.get(`${baseUrl()}${V3_DETAIL_PATH}/${id}`, { validateStatus: () => true });
    expect(res.status).toBe(200);
    expect(res.headers["content-type"] || "").toMatch(/application\/json/i);
    expect(res.data).toHaveProperty("id", id);
    expect("serviceName" in res.data || "name" in res.data).toBe(true);
    expect(res.data).toHaveProperty("description");
  });

  it("POST /v3/services accepts a valid postcode", async () => {
    const body = {
      postcode: "SW1A 1AA",
      distance: 10,
    };

    const res = await axios.post(`${baseUrl()}${V3_SEARCH_PATH}`, body, {
      validateStatus: () => true,
    });

    expect(res.status).toBe(200);
    const list = asArray(res.data);
    expect(Array.isArray(list)).toBe(true);
  });

  it("POST /v3/services rejects an invalid postcode", async () => {
    const body = {
      postcode: "NOT A POSTCODE",
      distance: 10,
    };

    const res = await axios.post(`${baseUrl()}${V3_SEARCH_PATH}`, body, {
      validateStatus: () => true,
    });

    expect(res.status).toBe(400);
    expect(res.data).toHaveProperty("postcode");
  });

  it("POST /v3/services works without postcode", async () => {
    // Distance on its own should be allowed to be omitted or ignored
    const body = {
      // postcode: omitted
      distance: 10,
    };

    const res = await axios.post(`${baseUrl()}${V3_SEARCH_PATH}`, body, {
      validateStatus: () => true,
    });

    expect(res.status).toBe(200);
    const list = asArray(res.data);
    expect(Array.isArray(list)).toBe(true);
  });

  it("GET /v3/service/3 should have a contact", async () => {
    const res = await axios.get(`${baseUrl()}${V3_DETAIL_PATH}/3`, {
      validateStatus: () => true,
    });

    expect(res.status).toBe(200);
    expect(res.data).toHaveProperty("contact");

    const contact = res.data.contact;
    expect(contact).toBeDefined();
    expect(typeof contact.name).toBe("string");
    // by spec, a present contact should have a non-empty name
    expect(contact.name.length).toBeGreaterThan(0);
    expect(contact).toHaveProperty("phone");
    expect(contact).toHaveProperty("email");
  });

  it("GET /v3/service/4 should NOT have a contact", async () => {
    const res = await axios.get(`${baseUrl()}${V3_DETAIL_PATH}/4`, {
      validateStatus: () => true,
    });

    expect(res.status).toBe(200);
    expect(res.data).toHaveProperty("contact");

    const contact = res.data.contact;
    // For “no contact”, serializer returns empty strings for all fields
    expect(contact).toBeDefined();
    expect(contact.name).toBe("");
    expect(contact.phone).toBe("");
    expect(contact.email).toBe("");
  });

  it("GET /v3/service/2 should have NO locations", async () => {
    const res = await axios.get(`${baseUrl()}${V3_DETAIL_PATH}/2`, {
      validateStatus: () => true,
    });

    expect(res.status).toBe(200);
    expect(res.data).toHaveProperty("locations");
    expect(Array.isArray(res.data.locations)).toBe(true);
    expect(res.data.locations.length).toBe(0);
  });

  it("GET /v3/service/1 should have 1 location", async () => {
    const res = await axios.get(`${baseUrl()}${V3_DETAIL_PATH}/1`, {
      validateStatus: () => true,
    });

    expect(res.status).toBe(200);
    expect(res.data).toHaveProperty("locations");
    expect(Array.isArray(res.data.locations)).toBe(true);
    expect(res.data.locations.length).toBe(1);
  });

  it("GET /v3/service/8 should have 3 locations", async () => {
    const res = await axios.get(`${baseUrl()}${V3_DETAIL_PATH}/8`, {
      validateStatus: () => true,
    });

    expect(res.status).toBe(200);
    expect(res.data).toHaveProperty("locations");
    expect(Array.isArray(res.data.locations)).toBe(true);
    expect(res.data.locations.length).toBe(3);
  });
});

it("POST /v3/services returns total and respects limit/offset", async () => {
  const body = { limit: 5, offset: 0 };

  const page1 = await axios.post(`${baseUrl()}${V3_SEARCH_PATH}`, body, {
    validateStatus: () => true,
  });
  expect(page1.status).toBe(200);

  const total = page1.data.total ?? asArray(page1.data).length;
  expect(typeof total).toBe("number");
  const page1Results = asArray(page1.data);
  expect(page1Results.length).toBeLessThanOrEqual(5);

  // second slice
  const page2 = await axios.post(
    `${baseUrl()}${V3_SEARCH_PATH}`,
    { limit: 5, offset: 5 },
    { validateStatus: () => true }
  );
  expect(page2.status).toBe(200);
  const page2Results = asArray(page2.data);

  // Ensure we don't get the same services again
  const ids1 = page1Results.map((r) => r.id);
  const ids2 = page2Results.map((r) => r.id);
  if (ids1.length && ids2.length) {
    expect(ids1.some((id) => ids2.includes(id))).toBe(false);
  }
});

it("POST /v3/services rejects invalid limit values", async () => {
  const tooLow = await axios.post(
    `${baseUrl()}${V3_SEARCH_PATH}`,
    { limit: 0 },
    { validateStatus: () => true }
  );
  expect(tooLow.status).toBe(400);
  expect(tooLow.data).toHaveProperty("limit");

  const tooHigh = await axios.post(
    `${baseUrl()}${V3_SEARCH_PATH}`,
    { limit: 1000 },
    { validateStatus: () => true }
  );
  expect(tooHigh.status).toBe(400);
  expect(tooHigh.data).toHaveProperty("limit");
});

it("POST /v3/services allows distance at 1 and 50 miles", async () => {
  for (const d of [1, 50]) {
    const res = await axios.post(
      `${baseUrl()}${V3_SEARCH_PATH}`,
      { postcode: "SW1A 1AA", distance: d },
      { validateStatus: () => true }
    );
    expect(res.status).toBe(200);
    const list = asArray(res.data);
    expect(Array.isArray(list)).toBe(true);
  }
});

it("POST /v3/services rejects distance > 50 miles", async () => {
  const res = await axios.post(
    `${baseUrl()}${V3_SEARCH_PATH}`,
    { postcode: "SW1A 1AA", distance: 50.1 },
    { validateStatus: () => true }
  );
  expect(res.status).toBe(400);
  expect(res.data).toHaveProperty("distance");
});

it("GET /v3/service/{id} returns 404 for unknown service", async () => {
  const res = await axios.get(`${baseUrl()}${V3_DETAIL_PATH}/999999`, {
    validateStatus: () => true,
  });

  expect(res.status).toBe(404);
  expect(res.data).toHaveProperty("error");
});

async function getServiceFromList(id: number) {
  const res = await axios.post(
    `${baseUrl()}${V3_SEARCH_PATH}`,
    { limit: 100, offset: 0 },
    { validateStatus: () => true }
  );
  expect(res.status).toBe(200);
  const list = asArray(res.data);
  return list.find((s) => s.id === id);
}

it("service 1 locations count is consistent between list and detail", async () => {
  const summary = await getServiceFromList(1);
  expect(summary).toBeDefined();
  expect(summary).toHaveProperty("locations");

  const detail = await axios.get(`${baseUrl()}${V3_DETAIL_PATH}/1`, {
    validateStatus: () => true,
  });
  expect(detail.status).toBe(200);
  expect(Array.isArray(detail.data.locations)).toBe(true);

  expect(summary.locations).toBe(detail.data.locations.length);
});

it("service 8 locations count is consistent between list and detail", async () => {
  const summary = await getServiceFromList(8);
  expect(summary).toBeDefined();
  expect(summary).toHaveProperty("locations");

  const detail = await axios.get(`${baseUrl()}${V3_DETAIL_PATH}/8`, {
    validateStatus: () => true,
  });
  expect(detail.status).toBe(200);
  expect(Array.isArray(detail.data.locations)).toBe(true);

  expect(summary.locations).toBe(detail.data.locations.length);
});

it("location without contact has empty contact object", async () => {
  const res = await axios.get(`${baseUrl()}${V3_DETAIL_PATH}/1`, {
    validateStatus: () => true,
  });
  expect(res.status).toBe(200);

  const locWithoutContact = res.data.locations.find(
    (loc: any) => loc.contact && !loc.contact.name
  );
  expect(locWithoutContact).toBeDefined();
  expect(locWithoutContact.contact).toEqual({
    name: "",
    phone: "",
    email: "",
  });
});

it("GET /v3/service/{id} with invalid distance params still returns 200", async () => {
  const res = await axios.get(
    `${baseUrl()}${V3_DETAIL_PATH}/1?postcode=NOTAPOST&distance=bananas`,
    { validateStatus: () => true }
  );
  expect(res.status).toBe(200);
  expect(Array.isArray(res.data.locations)).toBe(true);

  for (const loc of res.data.locations) {
    expect(loc).toHaveProperty("in_radius");
    expect(loc).toHaveProperty("distance");
  }
});

