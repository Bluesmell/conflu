export interface Space {
  id: number;
  key: string;
  name: string;
  description?: string;
}

export interface Page {
  id: number;
  title: string;
  space_key: string;
  raw_content: any;
  // parent_page?: number | null;
  // created_at: string;
  // updated_at: string;
  parent_page_id?: string | number | null; // Added for consistency with payload
}

// Payload for creating a new page
export interface PageCreatePayload {
  title: string;
  raw_content: any; // JSON object for ProseMirror content
  space_key: string; // Key of the space this page belongs to
  parent_page_id?: string | number; // Optional: ID of the parent page
}

// Payload for updating an existing page
export interface PageUpdatePayload {
  title: string;
  raw_content: any; // JSON object for ProseMirror content
  // space_key and parent_page_id are typically not updatable directly,
  // or would be part of a separate "move page" operation.
}

// For Page Search Results (corresponds to PageSearchSerializer in backend)
export interface PageSearchSerializer {
  id: number;
  title: string;
  slug: string;
  space_key: string | null;
  space_name: string | null;
  updated_at: string; // ISO date string
  headline: string; // HTML string with <mark> tags for highlights
  rank: number;
}

// --- User and Group Types ---
export interface User {
  id: number;
  username: string;
  email?: string; // Optional, might not always be present or needed
  first_name?: string;
  last_name?: string;
}

export interface Group {
  id: number;
  name: string;
}

// --- Space Permissions Types ---
export interface UserPermissionItem {
  user: User;
  permissions: string[]; // e.g., ["view_space", "edit_space_content"]
}

export interface GroupPermissionItem {
  group: Group;
  permissions: string[];
}

export interface SpacePermissionData {
  space_key: string;
  space_name: string;
  users: UserPermissionItem[];
  groups: GroupPermissionItem[];
}

export interface AssignPermissionPayload {
  user_id?: number; // One of user_id or group_id must be present
  group_id?: number;
  permission_codenames: string[];
}
