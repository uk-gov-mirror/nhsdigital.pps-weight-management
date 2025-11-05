import { DynamoDBClient, PutItemCommand, GetItemCommand } from "@aws-sdk/client-dynamodb";

const ddb = new DynamoDBClient({});
const TableName = process.env.TABLE_NAME!;

export const handler = async (event: any) => {

  // ---- Guard: only allow calls that carry the CloudFront secret header ----
  const headers = event?.headers || {};
  const secretHdr = headers['x-origin-secret'] ?? headers['X-Origin-Secret'];
  console.log("REQ", JSON.stringify({
    path: event?.requestContext?.http?.path,
    hasOriginSecret: Boolean(secretHdr),
    secretMatches: secretHdr === process.env.ORIGIN_SECRET
  }));
  if (secretHdr !== process.env.ORIGIN_SECRET) {
    return { statusCode: 403, headers: { "content-type": "application/json" }, body: JSON.stringify({ message: "Forbidden" }) };
  }
  // -------------------------------------------------------------------------

  try {
    const method = event?.requestContext?.http?.method;
    const path = event?.requestContext?.http?.path || "/";

    // Accept both forms (direct API vs via CloudFront)
    const isPublicPing = (method === "GET") && (path.startsWith("/public/api/ping"));
    if (isPublicPing) {
      return { statusCode: 200, headers: { "content-type": "text/plain" }, body: "pong" };
    }

    if ((method === "GET") && (path.startsWith("/secure/api/items/"))) {
      const id = path.split("/").pop();
      const res = await ddb.send(new GetItemCommand({
        TableName,
        Key: { pk: { S: `ITEM#${id}` }, sk: { S: `ITEM#${id}` } }
      }));
      return { statusCode: 200, body: JSON.stringify(res.Item ?? {}) };
    }

    if ((method === "POST") && (path === "/secure/api/items/")) {
      const userSub = event?.requestContext?.authorizer?.jwt?.claims?.sub ?? "anonymous";
      const body = JSON.parse(event.body ?? "{}");
      const id = body.id ?? Math.random().toString(36).slice(2);
      
      const item: any = {
        pk: { S: `ITEM#${id}` },
        sk: { S: `ITEM#${id}` },
        owner: { S: userSub }
      };

      // Loop through the body and add all properties to the item, except for the id
      for (const [key, value] of Object.entries(body)) {
        if (key !== 'id') {
          if (typeof value === 'string') {
            item[key] = { S: value };
          }
          // Add other types as needed (e.g., N for numbers, BOOL for booleans)
        }
      }

      await ddb.send(new PutItemCommand({
        TableName,
        Item: item
      }));
      return { statusCode: 201, body: JSON.stringify({ message: "Item created successfully." }) };
    }

    return { statusCode: 404, body: JSON.stringify({ message: "Not found" }) };
  } catch (err) {
    console.error(err);
    return {
      statusCode: 500,
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ message: "An unexpected error occurred." }),
    };
  }
};
