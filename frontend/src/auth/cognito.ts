import { config } from "../config";

/**
 * Cognito USER_PASSWORD_AUTH via the public Cognito Identity Provider endpoint.
 * The app client has no secret, so no AWS credentials are involved. Returns the
 * ID token, which the API Gateway Cognito authorizer validates.
 */
export async function cognitoLogin(email: string, password: string): Promise<string> {
  const { region, clientId } = config.cognito;
  if (!region || !clientId) throw new Error("Cognito is not configured (VITE_COGNITO_REGION / VITE_COGNITO_CLIENT_ID)");

  const res = await fetch(`https://cognito-idp.${region}.amazonaws.com/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-amz-json-1.1",
      "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
    },
    body: JSON.stringify({
      AuthFlow: "USER_PASSWORD_AUTH",
      ClientId: clientId,
      AuthParameters: { USERNAME: email, PASSWORD: password },
    }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data?.message ?? "Sign-in failed");
  if (data.ChallengeName) throw new Error(`Additional sign-in step required: ${data.ChallengeName}`);
  return data.AuthenticationResult.IdToken as string;
}
