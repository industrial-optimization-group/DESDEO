import { PUBLIC_API_URL } from "$env/static/public";

class ValidationError extends Error {
    public details: string[];

    constructor(message = "Validation error", details: string[] = []) {
        super(message);
        this.details = details;
        this.name = "ValidationError";
    }
}

export type LoginResponse = {
    access_token: string;
};

export enum UserRole {
    admin,
    analyst,
    dm,
    guest
};

export type UserInfo = {
    username: string;
    id: number;
    role: UserRole;
    group: string;
    access_token: string;
};

export type UserData = {
    user_info: UserInfo;
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
            console.error("Login failed:", response.statusText );
            throw new ValidationError("Login failed", ["Return code not 200"]);
        }

        const data: string = await response.json();

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
            throw new ValidationError("Could not refresh token", ["Return code not 200"]);
        }

        const data = await response.json();
        const new_access_token = data.access_token;


        return new_access_token;

    } catch (error) {
        console.error("An error occurred while refreshing the access token:", error);
        return null;
    }
}

export async function getUserDetails(access_token: string): Promise<UserInfo | null> {
    try {
        const url = PUBLIC_API_URL + "/user_info";
        const response = await fetch(url, {
            method: "GET",
            headers: {
                'Authorization': `Bearer ${access_token}`
            }
        });

        if (!response.ok) {
            console.error("Fetching user info failed:", response.statusText);
            throw new ValidationError("Fetching user info failed", ["Return code not 200"]);
        }

        const user_info: UserInfo = await response.json(); 

        return user_info;

    } catch (error) {
        return null;
    }
}