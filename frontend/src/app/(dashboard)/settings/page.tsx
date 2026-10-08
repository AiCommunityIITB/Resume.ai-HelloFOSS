"use client";

import { useState, useEffect, useRef } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { toast } from "sonner";
import api from '@/lib/api';
import { 
  Loader2, 
  Camera, 
  Save, 
  RotateCcw, 
  AlertTriangle, 
  CheckCircle2,
  User,
  GraduationCap,
  Calendar,
  Mail,
  Hash
} from 'lucide-react';
import MainLayout from '@/components/MainLayout';

const departments = [
  "Aerospace Engineering",
  "Biosciences and Bioengineering",
  "Chemical Engineering",
  "Chemistry",
  "Civil Engineering",
  "Computer Science & Engineering",
  "Earth Sciences",
  "Economics",
  "Electrical Engineering",
  "Energy Science and Engineering",
  "Environmental Science and Engineering (ESED)",
  "Humanities and Social Science (HSS)",
  "Industrial Engineering and Operations Research (IEOR)",
  "Mathematics",
  "Mechanical Engineering",
  "Metallurgical Engineering & Materials Science (MEMS)",
  "Physics",
];

const degrees = [
  "Bachelor of Technology (B.Tech)",
  "Bachelor of Science (B.S.)",
  "Bachelor of Design (B.Des)",
  "Dual Degree (B.Tech + M.Tech)",
  "Master of Technology (M.Tech)",
  "Master of Science (M.Sc.)",
  "Master of Design (M.Des.)",
  "Master of Business Administration (MBA)",
  "M.S. by Research",
  "Master in Public Policy (MPP)",
  "Master in Development Practice (MDP)",
  "Doctor of Philosophy (Ph.D.)",
];

interface FormErrors {
  username?: string;
  roll_number?: string;
  passing_year?: string;
}

export default function SettingsPage() {
  const { user, isLoading: isAuthLoading } = useAuth();
  const [formData, setFormData] = useState({
    username: '',
    roll_number: '',
    department: '',
    degree: '',
    passing_year: '',
  });
  const [originalData, setOriginalData] = useState(formData);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<FormErrors>({});
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [profileImage, setProfileImage] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (user) {
      const userData = {
        username: user.username || '',
        roll_number: user.roll_number || '',
        department: user.department || '',
        degree: user.degree || '',
        passing_year: user.passing_year?.toString() || '',
      };
      setFormData(userData);
      setOriginalData(userData);
      setProfileImage(user.profile_image || '');
    }
  }, [user]);

  useEffect(() => {
    const hasChanges = JSON.stringify(formData) !== JSON.stringify(originalData);
    setHasUnsavedChanges(hasChanges);
  }, [formData, originalData]);

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};

    if (!formData.username.trim()) {
      newErrors.username = 'Username is required';
    } else if (formData.username.length < 3) {
      newErrors.username = 'Username must be at least 3 characters';
    } else if (!/^[a-zA-Z0-9_-]+$/.test(formData.username)) {
      newErrors.username = 'Username can only contain letters, numbers, hyphens, and underscores';
    }

    if (!user?.is_sso_user) {
      if (!formData.roll_number.trim()) {
        newErrors.roll_number = 'Roll number is required';
      }

      if (formData.passing_year) {
        const year = parseInt(formData.passing_year, 10);
        const currentYear = new Date().getFullYear();
        if (year < currentYear - 10 || year > currentYear + 10) {
          newErrors.passing_year = `Passing year must be between ${currentYear - 10} and ${currentYear + 10}`;
        }
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    
    // Clear error when user starts typing
    if (errors[name as keyof FormErrors]) {
      setErrors(prev => ({ ...prev, [name]: undefined }));
    }
  };

  const handleDepartmentChange = (value: string) => {
    setFormData(prev => ({ ...prev, department: value }));
  };

  const handleDegreeChange = (value: string) => {
    setFormData(prev => ({ ...prev, degree: value }));
  };

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) { // 5MB limit
      toast.error('Image size should be less than 5MB');
      return;
    }

    if (!file.type.startsWith('image/')) {
      toast.error('Please select a valid image file');
      return;
    }

    // Create preview
    const reader = new FileReader();
    reader.onload = (e) => {
      setProfileImage(e.target?.result as string);
    };
    reader.readAsDataURL(file);

    // Here you would typically upload to your server
    // For now, just showing the preview
    toast.success('Profile image updated (preview)');
  };

  const resetForm = () => {
    setFormData(originalData);
    setErrors({});
    setProfileImage(user?.profile_image || '');
    toast.info('Form reset to saved values');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      toast.error('Please fix the errors before submitting');
      return;
    }

    setIsSubmitting(true);

    const payload: { [key: string]: any } = {
      username: formData.username.trim(),
    };
    
    if (!user?.is_sso_user) {
      payload.roll_number = formData.roll_number.trim();
      payload.department = formData.department;
      payload.degree = formData.degree;
      payload.passing_year = formData.passing_year ? parseInt(formData.passing_year, 10) : null;
    }

    try {
      const response = await api.put('/api/v1/profile', payload);
      if (response.data.success) {
        toast.success('Profile updated successfully!');
        setOriginalData(formData);
        setErrors({});
      } else {
        toast.error(response.data.message || 'Failed to update profile.');
      }
    } catch (error: any) {
      toast.error(error.response?.data?.message || 'An error occurred.');
    } finally {
      setIsSubmitting(false);
    }
  };
  
  if (isAuthLoading || !user) {
    return (
      <div className="flex items-center justify-center h-full min-h-[400px]">
        <div className="text-center space-y-4">
          <Loader2 className="h-8 w-8 animate-spin mx-auto" />
          <p className="text-muted-foreground">Loading your profile...</p>
        </div>
      </div>
    );
  }

  return (
    <MainLayout>
    <div className="max-w-4xl mx-auto space-y-8 pt-32">
      {/* Header Section */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <User className="h-5 w-5" />
          <h3 className="text-2xl font-bold">Profile Settings</h3>
        </div>
        <p className="text-muted-foreground">
          Manage your profile information and preferences. Changes are saved automatically.
        </p>
      </div>

      {/* Unsaved Changes Alert */}
      {hasUnsavedChanges && (
        <Alert className="border-orange-200 bg-orange-50 dark:border-orange-800 dark:bg-orange-950">
          <AlertTriangle className="h-4 w-4 text-orange-600" />
          <AlertDescription className="text-orange-800 dark:text-orange-200">
            You have unsaved changes. Don't forget to save your updates.
          </AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Profile Picture Card */}
        <Card className="lg:col-span-1">
          <CardHeader className="text-center">
            <CardTitle className="flex items-center justify-center gap-2">
              <Camera className="h-4 w-4" />
              Profile Picture
            </CardTitle>
          </CardHeader>
          <CardContent className="text-center space-y-4">
            <div className="relative inline-block">
              <Avatar className="h-32 w-32 mx-auto">
                <AvatarImage src={profileImage} alt="Profile" />
                <AvatarFallback className="text-2xl">
                  {user.username?.charAt(0)?.toUpperCase() || 'U'}
                </AvatarFallback>
              </Avatar>
              <Button
                size="sm"
                variant="secondary"
                className="absolute bottom-0 right-0 rounded-full h-8 w-8 p-0"
                onClick={() => fileInputRef.current?.click()}
              >
                <Camera className="h-4 w-4" />
              </Button>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleImageUpload}
              className="hidden"
            />
            <p className="text-sm text-muted-foreground">
              Click the camera icon to upload a new profile picture
            </p>
          </CardContent>
        </Card>

        {/* Profile Form */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <GraduationCap className="h-5 w-5" />
              Profile Information
            </CardTitle>
            <CardDescription>
              Update your personal and academic details below.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Basic Information */}
              <div className="space-y-4">
                <h4 className="font-medium flex items-center gap-2">
                  <User className="h-4 w-4" />
                  Basic Information
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="username" className="flex items-center gap-2">
                      <User className="h-3 w-3" />
                      Username
                    </Label>
                    <Input
                      id="username"
                      name="username"
                      value={formData.username}
                      onChange={handleChange}
                      className={errors.username ? 'border-red-500' : ''}
                      placeholder="Enter your username"
                    />
                    {errors.username && (
                      <p className="text-sm text-red-500">{errors.username}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="email" className="flex items-center gap-2">
                      <Mail className="h-3 w-3" />
                      Email
                      <Badge variant="secondary" className="text-xs">Verified</Badge>
                    </Label>
                    <Input
                      id="email"
                      name="email"
                      value={user.email}
                      disabled
                      className="bg-muted"
                    />
                  </div>
                </div>
              </div>

              <Separator />

              {/* Academic Information */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="font-medium flex items-center gap-2">
                    <GraduationCap className="h-4 w-4" />
                    Academic Information
                  </h4>
                  {user.is_sso_user && (
                    <Badge variant="outline" className="text-xs">
                      <CheckCircle2 className="h-3 w-3 mr-1" />
                      SSO Verified
                    </Badge>
                  )}
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="roll_number" className="flex items-center gap-2">
                      <Hash className="h-3 w-3" />
                      Roll Number
                      {user.is_sso_user && <Badge variant="secondary" className="text-xs">Auto-filled</Badge>}
                    </Label>
                    <Input
                      id="roll_number"
                      name="roll_number"
                      value={formData.roll_number}
                      onChange={handleChange}
                      disabled={user.is_sso_user}
                      className={`${errors.roll_number ? 'border-red-500' : ''} ${
                        user.is_sso_user ? 'bg-muted' : ''
                      }`}
                      placeholder="Enter your roll number"
                    />
                    {errors.roll_number && (
                      <p className="text-sm text-red-500">{errors.roll_number}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="passing_year" className="flex items-center gap-2">
                      <Calendar className="h-3 w-3" />
                      Passing Year
                    </Label>
                    <Input
                      id="passing_year"
                      name="passing_year"
                      type="number"
                      value={formData.passing_year}
                      onChange={handleChange}
                      disabled={user.is_sso_user}
                      className={`${errors.passing_year ? 'border-red-500' : ''} ${
                        user.is_sso_user ? 'bg-muted' : ''
                      }`}
                      placeholder="2025"
                      min="2015"
                      max="2035"
                    />
                    {errors.passing_year && (
                      <p className="text-sm text-red-500">{errors.passing_year}</p>
                    )}
                  </div>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="department">Department</Label>
                    <Select
                      value={formData.department}
                      onValueChange={handleDepartmentChange}
                      disabled={user.is_sso_user}
                    >
                      <SelectTrigger 
                        id="department" 
                        className={`w-full ${user.is_sso_user ? 'bg-muted' : ''}`}
                      >
                        <SelectValue placeholder="Select your department" />
                      </SelectTrigger>
                      <SelectContent>
                        {departments.map(dept => (
                          <SelectItem key={dept} value={dept}>
                            {dept}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="degree">Degree Program</Label>
                    <Select
                      value={formData.degree}
                      onValueChange={handleDegreeChange}
                      disabled={user.is_sso_user}
                    >
                      <SelectTrigger 
                        id="degree" 
                        className={`w-full ${user.is_sso_user ? 'bg-muted' : ''}`}
                      >
                        <SelectValue placeholder="Select your degree" />
                      </SelectTrigger>
                      <SelectContent>
                        {degrees.map(deg => (
                          <SelectItem key={deg} value={deg}>
                            {deg}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>

              <Separator />

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row gap-3 pt-4">
                <Button 
                  type="submit" 
                  disabled={isSubmitting || !hasUnsavedChanges}
                  className="flex-1 sm:flex-none"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="mr-2 h-4 w-4" />
                      Save Changes
                    </>
                  )}
                </Button>
                
                <Button
                  type="button"
                  variant="outline"
                  onClick={resetForm}
                  disabled={!hasUnsavedChanges || isSubmitting}
                  className="flex-1 sm:flex-none"
                >
                  <RotateCcw className="mr-2 h-4 w-4" />
                  Reset
                </Button>
              </div>

              {user.is_sso_user && (
                <Alert>
                  <CheckCircle2 className="h-4 w-4" />
                  <AlertDescription>
                    Your academic information is automatically synced from the SSO system and cannot be modified manually.
                  </AlertDescription>
                </Alert>
              )}
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
    </MainLayout>
  );
}
