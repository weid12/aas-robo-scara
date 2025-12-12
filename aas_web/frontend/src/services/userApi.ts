/**
 * ------------------------------------------------------------------------------------------------------------------
 * Serviço de API para gerenciamento de usuários.
 * Encapsula chamadas para endpoints de registro e consulta de usuários.
 * ------------------------------------------------------------------------------------------------------------------
 */

const API_BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:5000";

export interface UserCreate {
    username: string;
    email: string;
    full_name: string;
    password: string;
    department?: string;
    role?: string;
    profile_type?: string;
}

export interface UserUpdate {
    full_name?: string;
    email?: string;
    password?: string;
    role?: string;
    profile_type?: string;
    department?: string;
    is_active?: boolean;
}

export interface UserRead {
    id: number;
    username: string;
    email: string;
    full_name: string;
    department?: string;
    role: string;
    profile_type: string;
    created_at: string;
    is_active: boolean;
}

export interface UserList {
    users: UserRead[];
    total: number;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${path}`, options);

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Erro desconhecido" }));
        throw new Error(errorData.detail || `Falha ao buscar ${path}`);
    }

    return (await response.json()) as T;
}

export function registerUser(userData: UserCreate): Promise<UserRead> {
    return request<UserRead>("/api/users/register", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(userData),
    });
}

export function updateUser(userId: number, userData: UserUpdate): Promise<UserRead> {
    return request<UserRead>(`/api/users/users/${userId}`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(userData),
    });
}

export function listUsers(skip: number = 0, limit: number = 100): Promise<UserList> {
    return request<UserList>(`/api/users/users?skip=${skip}&limit=${limit}`);
}

export function getUser(userId: number): Promise<UserRead> {
    return request<UserRead>(`/api/users/users/${userId}`);
}
