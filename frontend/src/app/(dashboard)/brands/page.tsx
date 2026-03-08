"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Plus,
  Pencil,
  Package,
  Users,
  Megaphone,
  Loader2,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { api } from "@/lib/api";
import type { Brand, BrandCreatePayload, BrandUpdatePayload } from "@/types";

// ---------------------------------------------------------------------------
// Types for form state
// ---------------------------------------------------------------------------

interface ProductDraft {
  name: string;
  description: string;
  price: string;
  image_url: string;
}

interface AudienceDraft {
  name: string;
  demographics: string;
  interests: string;
}

interface BrandForm {
  name: string;
  voice: string;
  visual_guidelines: string;
  offers: string;
  products: ProductDraft[];
  audiences: AudienceDraft[];
}

const EMPTY_PRODUCT: ProductDraft = {
  name: "",
  description: "",
  price: "",
  image_url: "",
};

const EMPTY_AUDIENCE: AudienceDraft = {
  name: "",
  demographics: "",
  interests: "",
};

function brandToForm(brand: Brand): BrandForm {
  return {
    name: brand.name,
    voice: brand.voice ?? "",
    visual_guidelines: brand.visual_guidelines ?? "",
    offers: brand.offers
      ? brand.offers.map((o) => o.name ?? JSON.stringify(o)).join(", ")
      : "",
    products: brand.products.map((p) => ({
      name: p.name,
      description: p.description ?? "",
      price: p.price != null ? String(p.price) : "",
      image_url: p.image_url ?? "",
    })),
    audiences: brand.audiences.map((a) => ({
      name: a.name,
      demographics: a.demographics ?? "",
      interests: a.interests ?? "",
    })),
  };
}

function formToCreatePayload(form: BrandForm): BrandCreatePayload {
  return {
    name: form.name,
    voice: form.voice || null,
    visual_guidelines: form.visual_guidelines || null,
    offers: form.offers
      ? form.offers
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean)
          .map((name) => ({ name }))
      : null,
    products: form.products
      .filter((p) => p.name.trim())
      .map((p) => ({
        name: p.name,
        description: p.description || null,
        price: p.price ? Number(p.price) : null,
        image_url: p.image_url || null,
      })),
    audiences: form.audiences
      .filter((a) => a.name.trim())
      .map((a) => ({
        name: a.name,
        demographics: a.demographics || null,
        interests: a.interests || null,
      })),
  };
}

function formToUpdatePayload(form: BrandForm): BrandUpdatePayload {
  return formToCreatePayload(form);
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function BrandsPage() {
  const [brands, setBrands] = useState<Brand[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Dialog state
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingBrand, setEditingBrand] = useState<Brand | null>(null);
  const [form, setForm] = useState<BrandForm>({
    name: "",
    voice: "",
    visual_guidelines: "",
    offers: "",
    products: [],
    audiences: [],
  });
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const fetchBrands = useCallback(async () => {
    try {
      const data = await api.get<Brand[]>("/api/brands");
      setBrands(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load brands");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBrands();
  }, [fetchBrands]);

  // ------- Dialog helpers -------

  function openCreate() {
    setEditingBrand(null);
    setForm({
      name: "",
      voice: "",
      visual_guidelines: "",
      offers: "",
      products: [],
      audiences: [],
    });
    setSaveError(null);
    setDialogOpen(true);
  }

  function openEdit(brand: Brand) {
    setEditingBrand(brand);
    setForm(brandToForm(brand));
    setSaveError(null);
    setDialogOpen(true);
  }

  async function handleSave() {
    if (!form.name.trim()) {
      setSaveError("Brand name is required.");
      return;
    }
    setSaving(true);
    setSaveError(null);
    try {
      if (editingBrand) {
        await api.put<Brand>(
          `/api/brands/${editingBrand.id}`,
          formToUpdatePayload(form),
        );
      } else {
        await api.post<Brand>("/api/brands", formToCreatePayload(form));
      }
      setDialogOpen(false);
      await fetchBrands();
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Failed to save brand");
    } finally {
      setSaving(false);
    }
  }

  // ------- Product list helpers -------

  function addProduct() {
    setForm((f) => ({ ...f, products: [...f.products, { ...EMPTY_PRODUCT }] }));
  }

  function updateProduct(idx: number, field: keyof ProductDraft, value: string) {
    setForm((f) => ({
      ...f,
      products: f.products.map((p, i) =>
        i === idx ? { ...p, [field]: value } : p,
      ),
    }));
  }

  function removeProduct(idx: number) {
    setForm((f) => ({
      ...f,
      products: f.products.filter((_, i) => i !== idx),
    }));
  }

  // ------- Audience list helpers -------

  function addAudience() {
    setForm((f) => ({
      ...f,
      audiences: [...f.audiences, { ...EMPTY_AUDIENCE }],
    }));
  }

  function updateAudience(
    idx: number,
    field: keyof AudienceDraft,
    value: string,
  ) {
    setForm((f) => ({
      ...f,
      audiences: f.audiences.map((a, i) =>
        i === idx ? { ...a, [field]: value } : a,
      ),
    }));
  }

  function removeAudience(idx: number) {
    setForm((f) => ({
      ...f,
      audiences: f.audiences.filter((_, i) => i !== idx),
    }));
  }

  // ------- Render -------

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Brands</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Manage brands, products, audiences, and brand voice.
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4" />
          New Brand
        </Button>
      </div>

      {/* Error */}
      {error && <p className="text-sm text-destructive">{error}</p>}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* Empty state */}
      {!loading && brands.length === 0 && !error && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Megaphone className="h-10 w-10 text-muted-foreground/40" />
            <p className="mt-3 text-sm text-muted-foreground">
              No brands yet. Create your first brand to get started.
            </p>
            <Button className="mt-4" onClick={openCreate}>
              <Plus className="h-4 w-4" />
              New Brand
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Brand cards */}
      {!loading && brands.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {brands.map((brand) => (
            <Card
              key={brand.id}
              className="cursor-pointer transition-colors hover:border-primary/50 hover:shadow-md"
              onClick={() => openEdit(brand)}
            >
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">{brand.name}</CardTitle>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={(e) => {
                      e.stopPropagation();
                      openEdit(brand);
                    }}
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                </div>
                {brand.voice && (
                  <CardDescription className="line-clamp-2">
                    {brand.voice}
                  </CardDescription>
                )}
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-3">
                  <Badge variant="secondary" className="gap-1">
                    <Package className="h-3 w-3" />
                    {brand.products.length}{" "}
                    {brand.products.length === 1 ? "product" : "products"}
                  </Badge>
                  <Badge variant="secondary" className="gap-1">
                    <Users className="h-3 w-3" />
                    {brand.audiences.length}{" "}
                    {brand.audiences.length === 1 ? "audience" : "audiences"}
                  </Badge>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create / Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-h-[85vh] max-w-2xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingBrand ? `Edit ${editingBrand.name}` : "New Brand"}
            </DialogTitle>
            <DialogDescription>
              {editingBrand
                ? "Update brand details, products, and audiences."
                : "Create a new brand with products and audiences."}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-5">
            {/* Brand name */}
            <div className="space-y-2">
              <Label htmlFor="brand-name">Brand Name</Label>
              <Input
                id="brand-name"
                placeholder="e.g. GlowVita"
                value={form.name}
                onChange={(e) =>
                  setForm((f) => ({ ...f, name: e.target.value }))
                }
              />
            </div>

            {/* Voice */}
            <div className="space-y-2">
              <Label htmlFor="brand-voice">Brand Voice</Label>
              <Textarea
                id="brand-voice"
                placeholder="Describe the brand's tone and communication style..."
                rows={3}
                value={form.voice}
                onChange={(e) =>
                  setForm((f) => ({ ...f, voice: e.target.value }))
                }
              />
            </div>

            {/* Visual guidelines */}
            <div className="space-y-2">
              <Label htmlFor="brand-visual">Visual Guidelines</Label>
              <Textarea
                id="brand-visual"
                placeholder="Colors, fonts, photography style, aesthetic..."
                rows={3}
                value={form.visual_guidelines}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    visual_guidelines: e.target.value,
                  }))
                }
              />
            </div>

            {/* Offers */}
            <div className="space-y-2">
              <Label htmlFor="brand-offers">Offers</Label>
              <Input
                id="brand-offers"
                placeholder="Comma-separated, e.g. Buy 2 Get 1 Free, 30-Day Guarantee"
                value={form.offers}
                onChange={(e) =>
                  setForm((f) => ({ ...f, offers: e.target.value }))
                }
              />
            </div>

            <Separator />

            {/* Products */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label className="text-base font-semibold">Products</Label>
                <Button variant="outline" size="sm" onClick={addProduct}>
                  <Plus className="h-3.5 w-3.5" />
                  Add Product
                </Button>
              </div>

              {form.products.length === 0 && (
                <p className="text-sm text-muted-foreground">
                  No products yet. Add products to this brand.
                </p>
              )}

              {form.products.map((product, idx) => (
                <Card key={idx}>
                  <CardContent className="space-y-3 pt-4">
                    <div className="flex items-start justify-between">
                      <span className="text-sm font-medium text-muted-foreground">
                        Product {idx + 1}
                      </span>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => removeProduct(idx)}
                      >
                        <X className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="col-span-2 space-y-1">
                        <Label className="text-xs">Name</Label>
                        <Input
                          placeholder="Product name"
                          value={product.name}
                          onChange={(e) =>
                            updateProduct(idx, "name", e.target.value)
                          }
                        />
                      </div>
                      <div className="col-span-2 space-y-1">
                        <Label className="text-xs">Description</Label>
                        <Input
                          placeholder="Brief description"
                          value={product.description}
                          onChange={(e) =>
                            updateProduct(idx, "description", e.target.value)
                          }
                        />
                      </div>
                      <div className="space-y-1">
                        <Label className="text-xs">Price ($)</Label>
                        <Input
                          type="number"
                          min="0"
                          step="0.01"
                          placeholder="0.00"
                          value={product.price}
                          onChange={(e) =>
                            updateProduct(idx, "price", e.target.value)
                          }
                        />
                      </div>
                      <div className="space-y-1">
                        <Label className="text-xs">Image URL</Label>
                        <Input
                          placeholder="https://..."
                          value={product.image_url}
                          onChange={(e) =>
                            updateProduct(idx, "image_url", e.target.value)
                          }
                        />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            <Separator />

            {/* Audiences */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label className="text-base font-semibold">Audiences</Label>
                <Button variant="outline" size="sm" onClick={addAudience}>
                  <Plus className="h-3.5 w-3.5" />
                  Add Audience
                </Button>
              </div>

              {form.audiences.length === 0 && (
                <p className="text-sm text-muted-foreground">
                  No audiences yet. Add target audiences for this brand.
                </p>
              )}

              {form.audiences.map((audience, idx) => (
                <Card key={idx}>
                  <CardContent className="space-y-3 pt-4">
                    <div className="flex items-start justify-between">
                      <span className="text-sm font-medium text-muted-foreground">
                        Audience {idx + 1}
                      </span>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => removeAudience(idx)}
                      >
                        <X className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                    <div className="space-y-3">
                      <div className="space-y-1">
                        <Label className="text-xs">Name</Label>
                        <Input
                          placeholder="Audience segment name"
                          value={audience.name}
                          onChange={(e) =>
                            updateAudience(idx, "name", e.target.value)
                          }
                        />
                      </div>
                      <div className="space-y-1">
                        <Label className="text-xs">Demographics</Label>
                        <Input
                          placeholder="Age, gender, income, location..."
                          value={audience.demographics}
                          onChange={(e) =>
                            updateAudience(idx, "demographics", e.target.value)
                          }
                        />
                      </div>
                      <div className="space-y-1">
                        <Label className="text-xs">Interests</Label>
                        <Input
                          placeholder="Hobbies, preferences, lifestyle..."
                          value={audience.interests}
                          onChange={(e) =>
                            updateAudience(idx, "interests", e.target.value)
                          }
                        />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          {/* Save error */}
          {saveError && (
            <p className="text-sm text-destructive">{saveError}</p>
          )}

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDialogOpen(false)}
              disabled={saving}
            >
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving && <Loader2 className="h-4 w-4 animate-spin" />}
              {saving
                ? "Saving..."
                : editingBrand
                  ? "Update Brand"
                  : "Create Brand"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
