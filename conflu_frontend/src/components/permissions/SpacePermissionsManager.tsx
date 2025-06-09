import React, { useEffect, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import {
  getSpacePermissions,
  assignUserSpacePermission,
  assignGroupSpacePermission,
  removeUserFromSpacePermissions,
  removeGroupFromSpacePermissions,
  listUsers,
  listGroups,
} from '../../services/api';
import { SpacePermissionData, User, Group, UserPermissionItem, GroupPermissionItem } from '../../types/apiModels';
import styles from './SpacePermissionsManager.module.css'; // To be created

interface SpacePermissionsManagerProps {
  spaceKey: string;
}

const SpacePermissionsManager: React.FC<SpacePermissionsManagerProps> = ({ spaceKey }) => {
  const [permissionsData, setPermissionsData] = useState<SpacePermissionData | null>(null);
  const [allUsers, setAllUsers] = useState<User[]>([]);
  const [allGroups, setAllGroups] = useState<Group[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // State for adding/editing permissions
  const [selectedUser, setSelectedUser] = useState<string>(''); // User ID
  const [selectedGroup, setSelectedGroup] = useState<string>(''); // Group ID
  const [selectedPermissions, setSelectedPermissions] = useState<string[]>([]);

  const availablePermissions = ['view_space', 'edit_space_content', 'admin_space']; // Define available perms for the UI

  const loadPermissions = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await getSpacePermissions(spaceKey);
      setPermissionsData(data);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to load space permissions.");
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  }, [spaceKey]);

  const loadUsersAndGroups = useCallback(async () => {
    try {
      const [usersData, groupsData] = await Promise.all([listUsers(), listGroups()]);
      setAllUsers(usersData);
      setAllGroups(groupsData);
    } catch (err: any) {
      setError(err.message || "Failed to load users/groups.");
      console.error(err);
    }
  }, []);

  useEffect(() => {
    loadPermissions();
    loadUsersAndGroups();
  }, [loadPermissions, loadUsersAndGroups]);

  const handlePermissionChange = (perm: string) => {
    setSelectedPermissions(prev =>
      prev.includes(perm) ? prev.filter(p => p !== perm) : [...prev, perm]
    );
  };

  const handleAddUserPermissions = async () => {
    if (!selectedUser || selectedPermissions.length === 0) {
      alert("Please select a user and at least one permission.");
      return;
    }
    try {
      await assignUserSpacePermission(spaceKey, parseInt(selectedUser), selectedPermissions);
      loadPermissions(); // Refresh list
      setSelectedUser('');
      setSelectedPermissions([]);
    } catch (err: any) {
      alert(`Failed to assign permissions: ${err.message}`);
    }
  };

  const handleAddGroupPermissions = async () => {
    if (!selectedGroup || selectedPermissions.length === 0) {
      alert("Please select a group and at least one permission.");
      return;
    }
    try {
      await assignGroupSpacePermission(spaceKey, parseInt(selectedGroup), selectedPermissions);
      loadPermissions(); // Refresh list
      setSelectedGroup('');
      setSelectedPermissions([]);
    } catch (err: any) {
      alert(`Failed to assign permissions: ${err.message}`);
    }
  };

  const handleRemoveUser = async (userId: number) => {
    if (window.confirm("Are you sure you want to remove all permissions for this user?")) {
      try {
        await removeUserFromSpacePermissions(spaceKey, userId);
        loadPermissions();
      } catch (err: any) {
        alert(`Failed to remove user permissions: ${err.message}`);
      }
    }
  };

  const handleRemoveGroup = async (groupId: number) => {
     if (window.confirm("Are you sure you want to remove all permissions for this group?")) {
      try {
        await removeGroupFromSpacePermissions(spaceKey, groupId);
        loadPermissions();
      } catch (err: any) {
        alert(`Failed to remove group permissions: ${err.message}`);
      }
    }
  };


  if (isLoading && !permissionsData) {
    return <p>Loading permissions...</p>;
  }

  if (error) {
    return <p className={styles.errorMessage}>Error: {error}</p>;
  }

  if (!permissionsData) {
    return <p>No permissions data available.</p>;
  }

  return (
    <div className={styles.permissionsManager}>
      <h3>Manage Permissions for Space: {permissionsData.space_name} ({permissionsData.space_key})</h3>

      {/* Add User/Group Permissions Section */}
      <div className={styles.addPermissionSection}>
        <h4>Add/Update Permissions</h4>
        <div>
          <select value={selectedUser} onChange={e => { setSelectedUser(e.target.value); setSelectedGroup(''); }}>
            <option value="">Select User</option>
            {allUsers.map(user => <option key={user.id} value={user.id}>{user.username}</option>)}
          </select>
          <span> OR </span>
          <select value={selectedGroup} onChange={e => { setSelectedGroup(e.target.value); setSelectedUser(''); }}>
            <option value="">Select Group</option>
            {allGroups.map(group => <option key={group.id} value={group.id}>{group.name}</option>)}
          </select>
        </div>
        <div className={styles.checkboxGroup}>
          {availablePermissions.map(perm => (
            <label key={perm}>
              <input type="checkbox" checked={selectedPermissions.includes(perm)} onChange={() => handlePermissionChange(perm)} />
              {perm}
            </label>
          ))}
        </div>
        <button onClick={selectedUser ? handleAddUserPermissions : handleAddGroupPermissions} disabled={(!selectedUser && !selectedGroup) || selectedPermissions.length === 0}>
          {selectedUser ? 'Assign to User' : (selectedGroup ? 'Assign to Group' : 'Assign')}
        </button>
      </div>

      {/* Display Current User Permissions */}
      <div className={styles.currentPermissions}>
        <h4>User Permissions</h4>
        {permissionsData.users.length === 0 && <p>No users have explicit permissions.</p>}
        <ul>
          {permissionsData.users.map((item: UserPermissionItem) => (
            <li key={item.user.id}>
              <span>{item.user.username} ({item.user.email})</span>
              <span>[{item.permissions.join(', ')}]</span>
              <button onClick={() => handleRemoveUser(item.user.id)} className={styles.removeButton}>Remove</button>
            </li>
          ))}
        </ul>
      </div>

      {/* Display Current Group Permissions */}
      <div className={styles.currentPermissions}>
        <h4>Group Permissions</h4>
        {permissionsData.groups.length === 0 && <p>No groups have explicit permissions.</p>}
        <ul>
          {permissionsData.groups.map((item: GroupPermissionItem) => (
            <li key={item.group.id}>
              <span>{item.group.name}</span>
              <span>[{item.permissions.join(', ')}]</span>
              <button onClick={() => handleRemoveGroup(item.group.id)} className={styles.removeButton}>Remove</button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default SpacePermissionsManager;
