import type { Context } from "aws-lambda";

type Event = Record<string, unknown>;

export const handler = async (event: Event, context: Context) => {
  const started = Date.now();

  console.log(JSON.stringify({
    msg: "Daily Lambda invoked",
    requestId: context.awsRequestId,
    function: process.env.AWS_LAMBDA_FUNCTION_NAME,
    project: process.env.PROJECT,
    env: process.env.ENV,
    event,
  }));

  return {
    ok: true,
    ran_at_utc: new Date().toISOString(),
    duration_ms: Date.now() - started,
  };
};
