import { UserDTO } from "../../../contracts/users.contract";
import { User } from "../../../domain/entities/user.entity";

export class UserMapper {
  public static toDomain(dto: UserDTO): User {
    return new User(
      dto.id,
      dto.email,
      dto.name,
      dto.roles,
      dto.permissions
    );
  }
}
