import axios, { AxiosInstance } from "axios";
import { IAuthPort } from "../../domain/ports";
import { User } from "../../domain/entities/user.entity";
import { UserMapper } from "../api/mappers/user.mapper";
import { LoginRequestSchema, LoginResponseSchema, UserSchema } from "../../contracts";
import { env } from "../../config";
import {
  ValidationError,
  UnauthorizedError,
  ResourceNotFoundError,
  AppDomainError,
} from "../../domain/exceptions";

export class RestAuthService implements IAuthPort {
  private readonly client: AxiosInstance;

  constructor(clientInstance?: AxiosInstance) {
    this.client = clientInstance || axios.create({
      baseURL: env.BFF_URL,
      timeout: 5000,
    });
  }

  public async login(credentials: unknown): Promise<User> {
    try {
      // Validate credentials payload at boundary
      const validated = LoginRequestSchema.parse(credentials);
      
      const response = await this.client.post("/auth/login", {
        username: validated.username,
        password: validated.password,
      });

      LoginResponseSchema.parse(response.data);
      // BFF keeps access token in client memory context, or cookies proxy handles it.
      // We retrieve user profile metadata following login.
      return await this.getCurrentUser();
    } catch (error) {
      throw this.handleError(error);
    }
  }

  public async getCurrentUser(): Promise<User> {
    try {
      const response = await this.client.get("/auth/me");
      const validatedUser = UserSchema.parse(response.data);
      return UserMapper.toDomain(validatedUser);
    } catch (error) {
      throw this.handleError(error);
    }
  }

  public async logout(): Promise<void> {
    try {
      await this.client.post("/auth/logout");
    } catch (error) {
      throw this.handleError(error);
    }
  }

  private handleError(error: unknown): Error {
    if (axios.isAxiosError(error)) {
      const status = error.response?.status;
      const data = error.response?.data;
      const message = data?.message || data?.detail || error.message;

      switch (status) {
        case 400:
        case 422:
          return new ValidationError(message, data?.errors || {});
        case 401:
        case 403:
          return new UnauthorizedError(message);
        case 404:
          return new ResourceNotFoundError(message);
        default:
          return new AppDomainError(message, `AUTH_ERROR_${status || "UNKNOWN"}`);
      }
    }

    if (error instanceof Error) {
      return error;
    }

    return new AppDomainError("An unexpected authentication adapter error occurred", "AUTH_UNKNOWN_ERROR");
  }
}
export default RestAuthService;
