import axios from 'axios';

const API_BASE_URL = '/api/v1'; // Proxied to Django backend

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Import interfaces from the dedicated types file
import {
  Space, Page, PageCreatePayload, PageUpdatePayload, PageSearchSerializer,
  User, Group, SpacePermissionData, AssignPermissionPayload,
  FallbackMacro,
  MermaidValidationRequest, MermaidValidationResponse // Added Mermaid types
} from '../types/apiModels';
import { ConfluenceUpload } from '../types/importerModels';

// API Service Functions

// Spaces
export const fetchSpaces = async (): Promise<Space[]> => {
  const response = await apiClient.get<Space[]>('/spaces/');
  return response.data;
};

export const fetchSpaceDetails = async (spaceKey: string): Promise<Space> => {
  const response = await apiClient.get<Space>(`/spaces/${spaceKey}/`);
  return response.data;
};

// Pages
export const fetchPagesInSpace = async (spaceKey: string): Promise<Page[]> => {
  const response = await apiClient.get<Page[]>(`/spaces/${spaceKey}/pages/`);
  return response.data;
};

export const fetchPageDetails = async (pageId: string | number): Promise<Page> => {
  // The backend endpoint might be /api/v1/pages/{page_id}/
  // Or it might be nested under spaces like /api/v1/spaces/{space_key}/pages/{page_id}/
  // Assuming the former based on typical DRF setups for simplicity.
  // If page IDs are unique across spaces, /api/v1/pages/{page_id}/ is fine.
  // If page IDs are unique only *within* a space, then space_key is needed.
  // For now, let's assume global page IDs for /api/v1/pages/{page_id}/
  const response = await apiClient.get<Page>(`/pages/${pageId}/`);
  return response.data;
};

// Page Create and Update
// Payloads are now imported from apiModels.ts

export const createPage = async (
  spaceKey: string,
  title: string,
  rawContent: any,
  parentPageId?: string | number
): Promise<Page> => {
  const payload: PageCreatePayload = {
    title,
    raw_content: rawContent,
    space_key: spaceKey, // Include spaceKey in payload
  };
  if (parentPageId) {
    payload.parent_page_id = parentPageId;
  }
  // The backend API for creating a page could be /api/v1/pages/ and space is determined by space_key in payload
  // OR it could be /api/v1/spaces/{space_key}/pages/
  // Let's assume /api/v1/pages/ and the backend uses `space_key` from payload.
  // If your backend expects POST to /api/v1/spaces/{space_key}/pages/, change to:
  // const response = await apiClient.post<Page>(`/spaces/${spaceKey}/pages/`, { title, raw_content: rawContent, parent_page_id: parentPageId });
  const response = await apiClient.post<Page>('/pages/', payload);
  return response.data;
};


// Importer API
export const getConfluenceImportStatus = async (uploadId: string | number): Promise<ConfluenceUpload> => {
  const response = await apiClient.get<ConfluenceUpload>(`/io/import/confluence/status/${uploadId}/`);
  return response.data;
};

// Example: Function to initiate an import (actual implementation might be more complex, e.g., FormData for file)
// This is just a placeholder to show where it would go.
export const initiateConfluenceImport = async (file: File, targetWorkspaceId?: number, targetSpaceId?: number): Promise<ConfluenceUpload> => {
  const formData = new FormData();
  formData.append('file', file);
  if (targetWorkspaceId) {
    formData.append('target_workspace_id', String(target_workspace_id));
  }
  if (targetSpaceId) {
    formData.append('target_space_id', String(target_space_id));
  }

  const response = await apiClient.post<ConfluenceUpload>('/io/import/confluence/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const updatePage = async (
  pageId: string | number,
  title: string,
  rawContent: any
): Promise<Page> => {
  const payload: PageUpdatePayload = { title, raw_content: rawContent };
  // Assuming PATCH is preferred for updates, but PUT is also common.
  // Backend endpoint /api/v1/pages/{page_id}/
  const response = await apiClient.put<Page>(`/pages/${pageId}/`, payload);
  return response.data;
};


// Search API
export interface SearchParams {
  q: string;
  space_key?: string;
  // Add other potential filters like tags, author, etc.
  // page?: number; // For pagination
}

// The backend might return a paginated response like:
// { count: number, next: string | null, previous: string | null, results: PageSearchSerializer[] }
// For simplicity, this client function currently assumes it returns just the array of results.
// Adapt as needed based on actual backend response structure.
export const searchPages = async (params: SearchParams): Promise<PageSearchSerializer[]> => {
  const response = await apiClient.get<PageSearchSerializer[]>('/search/pages/', { params });
  // If backend returns paginated response:
  // const response = await apiClient.get<{ results: PageSearchSerializer[] }>('/search/pages/', { params });
  // return response.data.results;
  return response.data;
};


// Permissions API
export const getSpacePermissions = async (spaceKey: string): Promise<SpacePermissionData> => {
  const response = await apiClient.get<SpacePermissionData>(`/workspaces/spaces/${spaceKey}/permissions/`);
  return response.data;
};

export const assignUserSpacePermission = async (spaceKey: string, userId: number, permissions: string[]): Promise<any> => {
  const payload: AssignPermissionPayload = { user_id: userId, permission_codenames: permissions };
  const response = await apiClient.post(`/workspaces/spaces/${spaceKey}/permissions/user/`, payload);
  return response.data;
};

export const assignGroupSpacePermission = async (spaceKey: string, groupId: number, permissions: string[]): Promise<any> => {
  const payload: AssignPermissionPayload = { group_id: groupId, permission_codenames: permissions };
  const response = await apiClient.post(`/workspaces/spaces/${spaceKey}/permissions/group/`, payload);
  return response.data;
};

export const removeUserFromSpacePermissions = async (spaceKey: string, userId: number): Promise<any> => {
  const response = await apiClient.delete(`/workspaces/spaces/${spaceKey}/permissions/user/${userId}/`);
  return response.data;
};

export const removeGroupFromSpacePermissions = async (spaceKey: string, groupId: number): Promise<any> => {
  const response = await apiClient.delete(`/workspaces/spaces/${spaceKey}/permissions/group/${groupId}/`);
  return response.data;
};

// User and Group List API
export const listUsers = async (): Promise<User[]> => {
  const response = await apiClient.get<User[]>('/identity/users/');
  return response.data;
};

export const listGroups = async (): Promise<Group[]> => {
  const response = await apiClient.get<Group[]>('/identity/groups/');
  return response.data;
};

// FallbackMacro API
export const getFallbackMacroDetails = async (macroId: number): Promise<FallbackMacro> => {
  // Assuming the URL is /api/v1/io/fallback-macros/{macroId}/ based on Part 1 plan
  const response = await apiClient.get<FallbackMacro>(`/io/fallback-macros/${macroId}/`);
  return response.data;
};

// Diagram Validation API
export const validateMermaidSyntax = async (syntax: string): Promise<MermaidValidationResponse> => {
  const payload: MermaidValidationRequest = { syntax };
  // The task mentioned it might be in importer.views - if so, /api/v1/io/diagrams/validate/mermaid/
  // Adjusting to match the likely backend location based on previous tasks.
  const response = await apiClient.post<MermaidValidationResponse>('/io/diagrams/validate/mermaid/', payload);
  return response.data;
};


export default apiClient;
