import { PUBLIC_API_URL } from "$env/static/public";

type LoginResponse = {
    access_token: string;
    token_type: string;
}

export async function login(username: string, password: string): Promise<LoginResponse> {
    try {
        const url = PUBLIC_API_URL + "/login";
        const response = await fetch(url, {
            method: "POST",
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                username,
                password
            }),
            credentials: 'include',
        });

        if (!response.ok) {
            console.error("Login failed:", response.statusText )
        }

    const data: LoginResponse = await response.json();

    return data;

   } catch (error) {
    console.error("An error occurred while logging in:", error);
    
    return null;
   }

}

export async function refreshAccessToken(): Promise<string | null> {
    try {
        const url = PUBLIC_API_URL + "/refresh";
        const response = await fetch(url, {
            method: "POST",
            credentials: 'include',  // send the cookie with the refresh token
        });

        if (!response.ok) {
            console.error("Refresh token failed:", response.statusText);
            return null;
        }

        const data = await response.json();
        const new_access_token = data.access_token;


        return new_access_token;

    } catch (error) {
        console.error("An error occurred while refreshing the access token:", error);
        return null;
    }
}