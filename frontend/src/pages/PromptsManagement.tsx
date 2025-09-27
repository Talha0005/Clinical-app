import React, { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Loader2, Edit, Trash2, Plus, Save, X } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { apiFetchJson } from "@/lib/api";

interface Prompt {
  id: string;
  name: string;
  description: string;
  category: string;
  content: string;
  version: number;
  created_at: string;
  updated_at: string;
  is_active: boolean;
}

interface PromptFormData {
  id: string;
  name: string;
  description: string;
  category: string;
  content: string;
  is_active: boolean;
}

export const PromptsManagement: React.FC = () => {
  const { token } = useAuth();
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [editingPrompt, setEditingPrompt] = useState<Prompt | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [formData, setFormData] = useState<PromptFormData>({
    id: '',
    name: '',
    description: '',
    category: 'custom',
    content: '',
    is_active: true
  });

  const categories = [
    { value: 'system', label: 'System' },
    { value: 'medical', label: 'Medical' },
    { value: 'interface', label: 'Interface' },
    { value: 'custom', label: 'Custom' }
  ];

  // Load prompts on component mount
  useEffect(() => {
    loadPrompts();
  }, []);

  const loadPrompts = async () => {
    try {
      setLoading(true);
      const data = await apiFetchJson<Prompt[]>('/api/prompts', {
        auth: true,
        token
      });
      setPrompts(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load prompts');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdatePrompt = async (prompt: Prompt) => {
    try {
      const updateData = {
        name: prompt.name,
        description: prompt.description,
        content: prompt.content,
        category: prompt.category,
        is_active: prompt.is_active
      };

      await apiFetchJson(`/api/prompts/${prompt.id}`, {
        method: 'PUT',
        auth: true,
        token,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updateData)
      });

      setSuccess('Prompt updated successfully');
      setEditingPrompt(null);
      loadPrompts();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update prompt');
    }
  };

  const handleCreatePrompt = async () => {
    try {
      await apiFetchJson('/api/prompts', {
        method: 'POST',
        auth: true,
        token,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });

      setSuccess('Prompt created successfully');
      setShowCreateDialog(false);
      setFormData({
        id: '',
        name: '',
        description: '',
        category: 'custom',
        content: '',
        is_active: true
      });
      loadPrompts();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create prompt');
    }
  };

  const handleDeletePrompt = async (promptId: string) => {
    if (!window.confirm('Are you sure you want to delete this prompt?')) {
      return;
    }

    try {
      await apiFetchJson(`/api/prompts/${promptId}`, {
        method: 'DELETE',
        auth: true,
        token,
        headers: { 'Content-Type': 'application/json' }
      });

      setSuccess('Prompt deleted successfully');
      loadPrompts();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete prompt');
    }
  };

  const getCategoryBadgeColor = (category: string) => {
    const colors = {
      system: 'bg-blue-100 text-blue-800',
      medical: 'bg-green-100 text-green-800',
      interface: 'bg-purple-100 text-purple-800',
      custom: 'bg-gray-100 text-gray-800'
    };
    return colors[category as keyof typeof colors] || colors.custom;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="ml-2">Loading prompts...</span>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Prompts Management</h1>
          <p className="text-gray-600">Manage and edit AI prompts for model enhancement</p>
        </div>
        
        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              New Prompt
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Create New Prompt</DialogTitle>
              <DialogDescription>
                Create a new prompt template for the AI system.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="new-id">ID</Label>
                  <Input
                    id="new-id"
                    value={formData.id}
                    onChange={(e) => setFormData({ ...formData, id: e.target.value })}
                    placeholder="unique_prompt_id"
                  />
                </div>
                <div>
                  <Label htmlFor="new-category">Category</Label>
                  <Select
                    value={formData.category}
                    onValueChange={(value) => setFormData({ ...formData, category: value })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {categories.map(cat => (
                        <SelectItem key={cat.value} value={cat.value}>
                          {cat.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              <div>
                <Label htmlFor="new-name">Name</Label>
                <Input
                  id="new-name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Display name for this prompt"
                />
              </div>
              
              <div>
                <Label htmlFor="new-description">Description</Label>
                <Input
                  id="new-description"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Brief description of this prompt's purpose"
                />
              </div>
              
              <div>
                <Label htmlFor="new-content">Content</Label>
                <Textarea
                  id="new-content"
                  value={formData.content}
                  onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                  placeholder="Enter the prompt content..."
                  rows={8}
                />
              </div>
              
              <div className="flex items-center space-x-2">
                <Switch
                  id="new-active"
                  checked={formData.is_active}
                  onCheckedChange={(checked) => setFormData({ ...formData, is_active: checked })}
                />
                <Label htmlFor="new-active">Active</Label>
              </div>
            </div>
            
            <div className="flex justify-end space-x-2 pt-4">
              <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
                Cancel
              </Button>
              <Button onClick={handleCreatePrompt}>
                Create Prompt
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {error && (
        <Alert className="mb-6 border-red-200 bg-red-50">
          <AlertDescription className="text-red-800">{error}</AlertDescription>
        </Alert>
      )}

      {success && (
        <Alert className="mb-6 border-green-200 bg-green-50">
          <AlertDescription className="text-green-800">{success}</AlertDescription>
        </Alert>
      )}

      <Tabs defaultValue="all" className="space-y-6">
        <TabsList>
          <TabsTrigger value="all">All Prompts ({prompts.length})</TabsTrigger>
          <TabsTrigger value="system">System ({prompts.filter(p => p.category === 'system').length})</TabsTrigger>
          <TabsTrigger value="medical">Medical ({prompts.filter(p => p.category === 'medical').length})</TabsTrigger>
          <TabsTrigger value="interface">Interface ({prompts.filter(p => p.category === 'interface').length})</TabsTrigger>
          <TabsTrigger value="custom">Custom ({prompts.filter(p => p.category === 'custom').length})</TabsTrigger>
        </TabsList>

        <TabsContent value="all">
          <div className="grid gap-6">
            {prompts.map(prompt => (
              <PromptCard
                key={prompt.id}
                prompt={prompt}
                isEditing={editingPrompt?.id === prompt.id}
                onEdit={() => setEditingPrompt(prompt)}
                onSave={(updatedPrompt) => handleUpdatePrompt(updatedPrompt)}
                onCancel={() => setEditingPrompt(null)}
                onDelete={() => handleDeletePrompt(prompt.id)}
                getCategoryBadgeColor={getCategoryBadgeColor}
                formatDate={formatDate}
              />
            ))}
          </div>
        </TabsContent>

        {categories.map(category => (
          <TabsContent key={category.value} value={category.value}>
            <div className="grid gap-6">
              {prompts.filter(p => p.category === category.value).map(prompt => (
                <PromptCard
                  key={prompt.id}
                  prompt={prompt}
                  isEditing={editingPrompt?.id === prompt.id}
                  onEdit={() => setEditingPrompt(prompt)}
                  onSave={(updatedPrompt) => handleUpdatePrompt(updatedPrompt)}
                  onCancel={() => setEditingPrompt(null)}
                  onDelete={() => handleDeletePrompt(prompt.id)}
                  getCategoryBadgeColor={getCategoryBadgeColor}
                  formatDate={formatDate}
                />
              ))}
            </div>
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
};

interface PromptCardProps {
  prompt: Prompt;
  isEditing: boolean;
  onEdit: () => void;
  onSave: (prompt: Prompt) => void;
  onCancel: () => void;
  onDelete: () => void;
  getCategoryBadgeColor: (category: string) => string;
  formatDate: (date: string) => string;
}

const PromptCard: React.FC<PromptCardProps> = ({
  prompt,
  isEditing,
  onEdit,
  onSave,
  onCancel,
  onDelete,
  getCategoryBadgeColor,
  formatDate
}) => {
  const [editData, setEditData] = useState<Prompt>(prompt);

  useEffect(() => {
    setEditData(prompt);
  }, [prompt]);

  if (isEditing) {
    return (
      <Card>
        <CardHeader>
          <div className="flex justify-between items-start">
            <div className="space-y-2">
              <Input
                value={editData.name}
                onChange={(e) => setEditData({ ...editData, name: e.target.value })}
                className="text-lg font-semibold"
              />
              <Input
                value={editData.description}
                onChange={(e) => setEditData({ ...editData, description: e.target.value })}
                className="text-sm"
              />
            </div>
            <div className="flex space-x-2">
              <Button size="sm" onClick={() => onSave(editData)}>
                <Save className="h-4 w-4" />
              </Button>
              <Button size="sm" variant="outline" onClick={onCancel}>
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center space-x-4">
              <Badge className={getCategoryBadgeColor(editData.category)}>
                {editData.category}
              </Badge>
              <div className="flex items-center space-x-2">
                <Switch
                  checked={editData.is_active}
                  onCheckedChange={(checked) => setEditData({ ...editData, is_active: checked })}
                />
                <span className="text-sm">{editData.is_active ? 'Active' : 'Inactive'}</span>
              </div>
            </div>
            <Textarea
              value={editData.content}
              onChange={(e) => setEditData({ ...editData, content: e.target.value })}
              rows={12}
              className="font-mono text-sm"
            />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex justify-between items-start">
          <div>
            <CardTitle className="text-lg">{prompt.name}</CardTitle>
            <CardDescription>{prompt.description}</CardDescription>
          </div>
          <div className="flex space-x-2">
            <Button size="sm" variant="outline" onClick={onEdit}>
              <Edit className="h-4 w-4" />
            </Button>
            <Button size="sm" variant="outline" onClick={onDelete}>
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="flex items-center space-x-4">
            <Badge className={getCategoryBadgeColor(prompt.category)}>
              {prompt.category}
            </Badge>
            <Badge variant={prompt.is_active ? "default" : "secondary"}>
              {prompt.is_active ? 'Active' : 'Inactive'}
            </Badge>
            <span className="text-sm text-gray-500">v{prompt.version}</span>
          </div>
          <div className="bg-gray-50 p-4 rounded-lg">
            <pre className="text-sm whitespace-pre-wrap font-mono max-h-48 overflow-y-auto">
              {prompt.content}
            </pre>
          </div>
          <div className="text-xs text-gray-500 flex justify-between">
            <span>Created: {formatDate(prompt.created_at)}</span>
            <span>Updated: {formatDate(prompt.updated_at)}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};