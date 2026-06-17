import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface EmergencyContact {
  name: string;
  phone: string;
  relation: string;
  type: 'doctor' | 'family';
}

interface User {
  id: string;
  email: string;
  name: string;
  age: number;
  gender: string;
  bloodType: string;
  medicalConditions: string[];
  currentMedications: string[];
  emergencyContacts: EmergencyContact[];
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  signup: (email: string, password: string, name: string, age: number, bloodType: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => Promise<void>;
  updateProfile: (updates: Partial<User>) => Promise<{ success: boolean; error?: string }>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Mock user database (in real app, this would be backend)
const MOCK_USERS_KEY = 'healsense_mock_users';
const AUTH_TOKEN_KEY = 'healsense_auth_token';

// Default mock user (Umair Hakeem's account)
const DEFAULT_MOCK_USER = {
  id: '1',
  email: 'umair@healsense.com',
  password: 'password123',
  name: 'Umair Hakeem',
  age: 24,
  gender: 'Male',
  bloodType: 'O+',
  medicalConditions: [],
  currentMedications: [],
  emergencyContacts: [
    { name: 'Dr. Ahmed Khan', phone: '+92 300 1234567', relation: 'Primary Care Physician', type: 'doctor' as const },
    { name: 'Awais', phone: '03145647685', relation: 'Brother', type: 'family' as const }
  ],
};

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Initialize mock users and check for existing session
  useEffect(() => {
    initializeAuth();
  }, []);

  const initializeAuth = async () => {
    try {
      // Initialize mock users if not exists
      const existingUsers = localStorage.getItem(MOCK_USERS_KEY);
      if (!existingUsers) {
        localStorage.setItem(MOCK_USERS_KEY, JSON.stringify([DEFAULT_MOCK_USER]));
      }

      // Check for existing auth token
      const token = localStorage.getItem(AUTH_TOKEN_KEY);
      if (token) {
        const userId = JSON.parse(token).userId;
        const users = JSON.parse(localStorage.getItem(MOCK_USERS_KEY) || '[]');
        const foundUser = users.find((u: any) => u.id === userId);
        if (foundUser) {
          const { password, ...userWithoutPassword } = foundUser;
          setUser(userWithoutPassword);
        }
      }
    } catch (error) {
      console.error('Error initializing auth:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
    try {
      const users = JSON.parse(localStorage.getItem(MOCK_USERS_KEY) || '[]');
      const foundUser = users.find((u: any) => u.email.toLowerCase() === email.toLowerCase());

      if (!foundUser) {
        return { success: false, error: 'User not found' };
      }

      if (foundUser.password !== password) {
        return { success: false, error: 'Incorrect password' };
      }

      // Save auth token
      localStorage.setItem(AUTH_TOKEN_KEY, JSON.stringify({ userId: foundUser.id }));

      // Set user without password
      const { password: _, ...userWithoutPassword } = foundUser;
      setUser(userWithoutPassword);

      return { success: true };
    } catch (error) {
      return { success: false, error: 'Login failed. Please try again.' };
    }
  };

  const signup = async (
    email: string, 
    password: string, 
    name: string, 
    age: number, 
    bloodType: string
  ): Promise<{ success: boolean; error?: string }> => {
    try {
      const users = JSON.parse(localStorage.getItem(MOCK_USERS_KEY) || '[]');
      
      // Check if user already exists
      if (users.find((u: any) => u.email.toLowerCase() === email.toLowerCase())) {
        return { success: false, error: 'Email already registered' };
      }

      // Create new user
      const newUser = {
        id: Date.now().toString(),
        email,
        password,
        name,
        age,
        gender: '',
        bloodType,
        medicalConditions: [],
        currentMedications: [],
        emergencyContacts: [],
      };

      users.push(newUser);
      localStorage.setItem(MOCK_USERS_KEY, JSON.stringify(users));

      // Auto login after signup
      localStorage.setItem(AUTH_TOKEN_KEY, JSON.stringify({ userId: newUser.id }));

      const { password: _, ...userWithoutPassword } = newUser;
      setUser(userWithoutPassword);

      return { success: true };
    } catch (error) {
      return { success: false, error: 'Signup failed. Please try again.' };
    }
  };

  const logout = async (): Promise<void> => {
    try {
      localStorage.removeItem(AUTH_TOKEN_KEY);
      setUser(null);
    } catch (error) {
      console.error('Error during logout:', error);
    }
  };

  const updateProfile = async (updates: Partial<User>): Promise<{ success: boolean; error?: string }> => {
    try {
      if (!user) {
        return { success: false, error: 'No user logged in' };
      }

      const users = JSON.parse(localStorage.getItem(MOCK_USERS_KEY) || '[]');
      const userIndex = users.findIndex((u: any) => u.id === user.id);

      if (userIndex === -1) {
        return { success: false, error: 'User not found' };
      }

      // Update user in mock database
      users[userIndex] = { ...users[userIndex], ...updates };
      localStorage.setItem(MOCK_USERS_KEY, JSON.stringify(users));

      // Update current user state
      setUser({ ...user, ...updates });

      return { success: true };
    } catch (error) {
      return { success: false, error: 'Failed to update profile' };
    }
  };

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: !!user,
    login,
    signup,
    logout,
    updateProfile,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
