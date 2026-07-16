export class User {
  constructor(
    public readonly id: string,
    public readonly email: string,
    public readonly name: string,
    public readonly roles: string[],
    public readonly permissions: string[]
  ) {}

  public hasRole(role: string): boolean {
    return this.roles.includes(role);
  }

  public hasPermission(permission: string): boolean {
    return this.permissions.includes(permission) || this.roles.includes("admin");
  }
}
