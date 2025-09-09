export enum Permission {
  /// Allow access to the menu item
  Allow,
  /// Deny access to the menu item
  Denied,
  /// Pending access to the menu item, e.g., waiting for a user role to be set
  Pending
}
