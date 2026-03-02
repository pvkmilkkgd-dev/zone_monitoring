import { useEffect, useState } from "react";
import { Modal } from "../components/Modal";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { requireEditor, handleAuthError, logout, isAdmin } from "../utils/auth";
import {
  getLayers,
  createLayer,
  updateLayer,
  deleteLayer,
  createSubLayer,
  updateSubLayer,
  deleteSubLayer,
  createSubSubLayer,
  updateSubSubLayer,
  deleteSubSubLayer,
  reorderLayers,
  reorderSubLayers,
  reorderSubSubLayers,
  type Layer,
  type SubLayer,
  type SubSubLayer,
} from "../api/layers";

type AddModalType = 'layer' | 'sublayer' | 'subsublayer';

// Sortable компонент для под-вложенного слоя (3-й уровень)
function SortableSubSubLayerItem({
  subSubLayer,
  onToggleVisibility,
  onDelete,
}: {
  subSubLayer: SubSubLayer;
  onToggleVisibility: (s: SubSubLayer) => void;
  onDelete: (id: number, name: string) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: `subsublayer-${subSubLayer.id}`,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex items-center justify-between p-3 pl-20 border-b border-slate-700/20 last:border-b-0 bg-slate-800/20"
    >
      <div className="flex items-center gap-3">
        <button
          {...attributes}
          {...listeners}
          className="w-4 h-4 text-slate-500 hover:text-slate-300 cursor-grab active:cursor-grabbing"
          title="Перетащите для сортировки"
        >
          ⋮⋮
        </button>
        <button
          onClick={() => onToggleVisibility(subSubLayer)}
          className={`w-3.5 h-3.5 rounded border-2 flex items-center justify-center transition ${
            subSubLayer.is_visible
              ? "border-violet-500 bg-violet-500 text-white"
              : "border-slate-500 bg-transparent"
          }`}
        >
          {subSubLayer.is_visible && <span className="text-[8px]">✓</span>}
        </button>
        <span className="text-sm text-slate-400">{subSubLayer.name}</span>
      </div>
      <button
        onClick={() => onDelete(subSubLayer.id, subSubLayer.name)}
        className="px-2 py-1 text-xs text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded transition"
      >
        Удалить
      </button>
    </div>
  );
}

// Sortable компонент для вложенного слоя (2-й уровень)
function SortableSubLayerItem({
  subLayer,
  isExpanded,
  onToggleExpand,
  onToggleVisibility,
  onOpenAddModal,
  onDelete,
  onToggleSubSubLayerVisibility,
  onDeleteSubSubLayer,
  onSubSubLayerDragEnd,
}: {
  subLayer: SubLayer;
  isExpanded: boolean;
  onToggleExpand: (id: number) => void;
  onToggleVisibility: (s: SubLayer) => void;
  onOpenAddModal: (type: AddModalType, parentId: number, parentName: string) => void;
  onDelete: (id: number, name: string) => void;
  onToggleSubSubLayerVisibility: (s: SubSubLayer) => void;
  onDeleteSubSubLayer: (id: number, name: string) => void;
  onSubSubLayerDragEnd: (event: DragEndEvent, subLayerId: number) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: `sublayer-${subLayer.id}`,
  });

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={style}>
      <div className="flex items-center justify-between p-3 pl-12 bg-slate-800/30 border-b border-slate-700/30">
        <div className="flex items-center gap-3">
          <button
            {...attributes}
            {...listeners}
            className="w-4 h-4 text-slate-500 hover:text-slate-300 cursor-grab active:cursor-grabbing"
            title="Перетащите для сортировки"
          >
            ⋮⋮
          </button>
          <button
            onClick={() => onToggleExpand(subLayer.id)}
            className="w-5 h-5 flex items-center justify-center text-slate-400 hover:text-slate-200 transition text-xs"
          >
            {isExpanded ? "▼" : "▶"}
          </button>
          <button
            onClick={() => onToggleVisibility(subLayer)}
            className={`w-4 h-4 rounded border-2 flex items-center justify-center transition ${
              subLayer.is_visible
                ? "border-emerald-500 bg-emerald-500 text-white"
                : "border-slate-500 bg-transparent"
            }`}
          >
            {subLayer.is_visible && <span className="text-[10px]">✓</span>}
          </button>
          <span className="text-sm text-slate-300">{subLayer.name}</span>
          {(subLayer.sub_sub_layers?.length || 0) > 0 && (
            <span className="text-xs text-slate-500">
              ({subLayer.sub_sub_layers?.length || 0})
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onOpenAddModal('subsublayer', subLayer.id, subLayer.name)}
            className="w-5 h-5 inline-flex items-center justify-center rounded bg-violet-500/20 text-violet-400 hover:bg-violet-500/30 transition"
            title="Добавить под-вложенный слой"
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M12 4v16m8-8H4" />
            </svg>
          </button>
          <button
            onClick={() => onDelete(subLayer.id, subLayer.name)}
            className="px-2 py-1 text-xs text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded transition"
          >
            Удалить
          </button>
        </div>
      </div>

      {/* Под-вложенные слои (3-й уровень) */}
      {isExpanded && (
        <div className="bg-slate-800/20">
          {(subLayer.sub_sub_layers?.length || 0) === 0 ? (
            <div className="p-3 pl-20 text-slate-500 text-xs">
              Нет под-вложенных слоев
            </div>
          ) : (
            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              onDragEnd={(e) => onSubSubLayerDragEnd(e, subLayer.id)}
            >
              <SortableContext
                items={(subLayer.sub_sub_layers || []).map(ss => `subsublayer-${ss.id}`)}
                strategy={verticalListSortingStrategy}
              >
                {(subLayer.sub_sub_layers || []).map((subSubLayer) => (
                  <SortableSubSubLayerItem
                    key={subSubLayer.id}
                    subSubLayer={subSubLayer}
                    onToggleVisibility={onToggleSubSubLayerVisibility}
                    onDelete={onDeleteSubSubLayer}
                  />
                ))}
              </SortableContext>
            </DndContext>
          )}
        </div>
      )}
    </div>
  );
}

// Sortable компонент для главного слоя (1-й уровень)
function SortableLayerItem({
  layer,
  isExpanded,
  expandedSubLayers,
  onToggleExpand,
  onToggleVisibility,
  onOpenAddModal,
  onDelete,
  onToggleSubLayerExpand,
  onToggleSubLayerVisibility,
  onDeleteSubLayer,
  onToggleSubSubLayerVisibility,
  onDeleteSubSubLayer,
  onSubLayerDragEnd,
  onSubSubLayerDragEnd,
}: {
  layer: Layer;
  isExpanded: boolean;
  expandedSubLayers: Set<number>;
  onToggleExpand: (id: number) => void;
  onToggleVisibility: (l: Layer) => void;
  onOpenAddModal: (type: AddModalType, parentId: number | null, parentName: string) => void;
  onDelete: (id: number, name: string) => void;
  onToggleSubLayerExpand: (id: number) => void;
  onToggleSubLayerVisibility: (s: SubLayer) => void;
  onDeleteSubLayer: (id: number, name: string) => void;
  onToggleSubSubLayerVisibility: (s: SubSubLayer) => void;
  onDeleteSubSubLayer: (id: number, name: string) => void;
  onSubLayerDragEnd: (event: DragEndEvent, layerId: number) => void;
  onSubSubLayerDragEnd: (event: DragEndEvent, subLayerId: number) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: `layer-${layer.id}`,
  });

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} className="border border-slate-700/50 rounded-lg overflow-hidden">
      {/* Главный слой */}
      <div className="flex items-center justify-between p-3 bg-slate-800/50">
        <div className="flex items-center gap-3">
          <button
            {...attributes}
            {...listeners}
            className="w-5 h-5 text-slate-500 hover:text-slate-300 cursor-grab active:cursor-grabbing"
            title="Перетащите для сортировки"
          >
            ⋮⋮
          </button>
          <button
            onClick={() => onToggleExpand(layer.id)}
            className="w-6 h-6 flex items-center justify-center text-slate-400 hover:text-slate-200 transition"
          >
            {isExpanded ? "▼" : "▶"}
          </button>
          <button
            onClick={() => onToggleVisibility(layer)}
            className={`w-5 h-5 rounded border-2 flex items-center justify-center transition ${
              layer.is_visible
                ? "border-sky-500 bg-sky-500 text-white"
                : "border-slate-500 bg-transparent"
            }`}
          >
            {layer.is_visible && <span className="text-xs">✓</span>}
          </button>
          <span className="text-sm font-medium text-slate-200">{layer.name}</span>
          <span className="text-xs text-slate-500">({layer.sub_layers.length})</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onOpenAddModal('sublayer', layer.id, layer.name)}
            className="w-6 h-6 inline-flex items-center justify-center rounded bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 transition"
            title="Добавить вложенный слой"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
            </svg>
          </button>
          <button
            onClick={() => onDelete(layer.id, layer.name)}
            className="px-2 py-1 text-xs text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded transition"
          >
            Удалить
          </button>
        </div>
      </div>

      {/* Вложенные слои (2-й уровень) */}
      {isExpanded && (
        <div className="border-t border-slate-700/50">
          {layer.sub_layers.length === 0 ? (
            <div className="p-3 pl-12 text-slate-500 text-xs">
              Нет вложенных слоев
            </div>
          ) : (
            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              onDragEnd={(e) => onSubLayerDragEnd(e, layer.id)}
            >
              <SortableContext
                items={layer.sub_layers.map(sl => `sublayer-${sl.id}`)}
                strategy={verticalListSortingStrategy}
              >
                {layer.sub_layers.map((subLayer) => (
                  <SortableSubLayerItem
                    key={subLayer.id}
                    subLayer={subLayer}
                    isExpanded={expandedSubLayers.has(subLayer.id)}
                    onToggleExpand={onToggleSubLayerExpand}
                    onToggleVisibility={onToggleSubLayerVisibility}
                    onOpenAddModal={onOpenAddModal}
                    onDelete={onDeleteSubLayer}
                    onToggleSubSubLayerVisibility={onToggleSubSubLayerVisibility}
                    onDeleteSubSubLayer={onDeleteSubSubLayer}
                    onSubSubLayerDragEnd={onSubSubLayerDragEnd}
                  />
                ))}
              </SortableContext>
            </DndContext>
          )}
        </div>
      )}
    </div>
  );
}

export function LayersPage() {
  const [layers, setLayers] = useState<Layer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Модальное окно добавления
  const [addModal, setAddModal] = useState<{
    open: boolean;
    type: AddModalType;
    parentId: number | null;
    parentName: string;
  }>({ open: false, type: 'layer', parentId: null, parentName: '' });
  const [newName, setNewName] = useState("");
  const [addError, setAddError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  
  // Модальное окно удаления
  const [deleteModal, setDeleteModal] = useState<{ 
    open: boolean; 
    type: 'layer' | 'sublayer' | 'subsublayer'; 
    id: number | null; 
    name: string;
  }>({ open: false, type: 'layer', id: null, name: '' });
  
  // Модальное окно успеха
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  
  // Развернутые слои
  const [expandedLayers, setExpandedLayers] = useState<Set<number>>(new Set());
  const [expandedSubLayers, setExpandedSubLayers] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (!requireEditor()) return;
    loadLayers();
  }, []);

  const loadLayers = async () => {
    try {
      setLoading(true);
      const data = await getLayers();
      setLayers(data);
      setError(null);
    } catch (e: any) {
      console.error(e);
      if (handleAuthError(e)) return;
      setError(e.message || "Ошибка загрузки слоев");
    } finally {
      setLoading(false);
    }
  };

  const openAddModal = (type: AddModalType, parentId: number | null = null, parentName: string = '') => {
    setAddModal({ open: true, type, parentId, parentName });
    setNewName("");
    setAddError(null);
  };

  const closeAddModal = () => {
    setAddModal({ open: false, type: 'layer', parentId: null, parentName: '' });
    setNewName("");
    setAddError(null);
  };

  const handleAdd = async () => {
    if (!newName.trim()) {
      setAddError("Введите название");
      return;
    }
    
    try {
      setSaving(true);
      setAddError(null);
      const name = newName.trim();
      
      if (addModal.type === 'layer') {
        // Проверка дублирования
        if (layers.some(l => l.name.toLowerCase() === name.toLowerCase())) {
          setAddError("Слой с таким названием уже существует");
          return;
        }
        await createLayer({ name, map_id: 1 });
      } else if (addModal.type === 'sublayer' && addModal.parentId) {
        const parent = layers.find(l => l.id === addModal.parentId);
        if (parent?.sub_layers.some(s => s.name.toLowerCase() === name.toLowerCase())) {
          setAddError("Вложенный слой с таким названием уже существует");
          return;
        }
        await createSubLayer({ name, parent_layer_id: addModal.parentId });
        setExpandedLayers(prev => new Set(prev).add(addModal.parentId!));
      } else if (addModal.type === 'subsublayer' && addModal.parentId) {
        const allSubs = layers.flatMap(l => l.sub_layers);
        const parent = allSubs.find(s => s.id === addModal.parentId);
        if (parent?.sub_sub_layers?.some(ss => ss.name.toLowerCase() === name.toLowerCase())) {
          setAddError("Под-вложенный слой с таким названием уже существует");
          return;
        }
        await createSubSubLayer({ name, parent_sub_layer_id: addModal.parentId });
        setExpandedSubLayers(prev => new Set(prev).add(addModal.parentId!));
      }
      
      await loadLayers();
      closeAddModal();
      
      const typeNames = { layer: 'Слой', sublayer: 'Вложенный слой', subsublayer: 'Под-вложенный слой' };
      setSuccessMessage(`${typeNames[addModal.type]} "${name}" успешно добавлен`);
    } catch (e: any) {
      console.error(e);
      if (handleAuthError(e)) return;
      setAddError(e.response?.data?.detail || e.message || "Ошибка при добавлении");
    } finally {
      setSaving(false);
    }
  };

  const toggleLayerVisibility = async (layer: Layer) => {
    try {
      await updateLayer(layer.id, { is_visible: !layer.is_visible });
      await loadLayers();
    } catch (e: any) {
      console.error(e);
      if (handleAuthError(e)) return;
    }
  };

  const toggleSubLayerVisibility = async (subLayer: SubLayer) => {
    try {
      await updateSubLayer(subLayer.id, { is_visible: !subLayer.is_visible });
      await loadLayers();
    } catch (e: any) {
      console.error(e);
      if (handleAuthError(e)) return;
    }
  };

  const toggleSubSubLayerVisibility = async (subSubLayer: SubSubLayer) => {
    try {
      await updateSubSubLayer(subSubLayer.id, { is_visible: !subSubLayer.is_visible });
      await loadLayers();
    } catch (e: any) {
      console.error(e);
      if (handleAuthError(e)) return;
    }
  };

  const openDeleteModal = (type: 'layer' | 'sublayer' | 'subsublayer', id: number, name: string) => {
    setDeleteModal({ open: true, type, id, name });
  };

  const confirmDelete = async () => {
    if (!deleteModal.id) return;
    
    try {
      if (deleteModal.type === 'layer') {
        await deleteLayer(deleteModal.id);
      } else if (deleteModal.type === 'sublayer') {
        await deleteSubLayer(deleteModal.id);
      } else {
        await deleteSubSubLayer(deleteModal.id);
      }
      
      await loadLayers();
      setDeleteModal({ open: false, type: 'layer', id: null, name: '' });
      const typeNames = { layer: 'Слой', sublayer: 'Вложенный слой', subsublayer: 'Под-вложенный слой' };
      setSuccessMessage(`${typeNames[deleteModal.type]} "${deleteModal.name}" успешно удален`);
    } catch (e: any) {
      console.error(e);
      if (handleAuthError(e)) return;
    }
  };

  const toggleExpanded = (layerId: number) => {
    setExpandedLayers(prev => {
      const next = new Set(prev);
      if (next.has(layerId)) {
        next.delete(layerId);
      } else {
        next.add(layerId);
      }
      return next;
    });
  };

  const toggleSubLayerExpanded = (subLayerId: number) => {
    setExpandedSubLayers(prev => {
      const next = new Set(prev);
      if (next.has(subLayerId)) {
        next.delete(subLayerId);
      } else {
        next.add(subLayerId);
      }
      return next;
    });
  };

  const handleLogout = () => {
    logout();
    window.location.href = "/";
  };

  // Drag-and-drop sensors
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  // Handler для перетаскивания главных слоёв
  const handleLayerDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const activeId = Number(String(active.id).replace('layer-', ''));
    const overId = Number(String(over.id).replace('layer-', ''));
    
    const oldIndex = layers.findIndex(l => l.id === activeId);
    const newIndex = layers.findIndex(l => l.id === overId);
    
    if (oldIndex !== -1 && newIndex !== -1) {
      const newLayers = arrayMove(layers, oldIndex, newIndex);
      setLayers(newLayers);
      
      // Сохраняем новый порядок на сервере
      try {
        const items = newLayers.map((l, idx) => ({ id: l.id, order: idx + 1 }));
        await reorderLayers(items);
      } catch (e) {
        console.error("Ошибка сохранения порядка:", e);
        await loadLayers(); // Восстанавливаем при ошибке
      }
    }
  };

  // Handler для перетаскивания вложенных слоёв
  const handleSubLayerDragEnd = async (event: DragEndEvent, layerId: number) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const activeId = Number(String(active.id).replace('sublayer-', ''));
    const overId = Number(String(over.id).replace('sublayer-', ''));
    
    const layer = layers.find(l => l.id === layerId);
    if (!layer) return;
    
    const oldIndex = layer.sub_layers.findIndex(sl => sl.id === activeId);
    const newIndex = layer.sub_layers.findIndex(sl => sl.id === overId);
    
    if (oldIndex !== -1 && newIndex !== -1) {
      const newSubLayers = arrayMove(layer.sub_layers, oldIndex, newIndex);
      const newLayers = layers.map(l => 
        l.id === layerId ? { ...l, sub_layers: newSubLayers } : l
      );
      setLayers(newLayers);
      
      try {
        const items = newSubLayers.map((sl, idx) => ({ id: sl.id, order: idx + 1 }));
        await reorderSubLayers(items);
      } catch (e) {
        console.error("Ошибка сохранения порядка:", e);
        await loadLayers();
      }
    }
  };

  // Handler для перетаскивания под-вложенных слоёв
  const handleSubSubLayerDragEnd = async (event: DragEndEvent, subLayerId: number) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const activeId = Number(String(active.id).replace('subsublayer-', ''));
    const overId = Number(String(over.id).replace('subsublayer-', ''));
    
    // Найти sublayer
    let foundLayer: Layer | undefined;
    let foundSubLayer: SubLayer | undefined;
    
    for (const l of layers) {
      const sl = l.sub_layers.find(s => s.id === subLayerId);
      if (sl) {
        foundLayer = l;
        foundSubLayer = sl;
        break;
      }
    }
    
    if (!foundLayer || !foundSubLayer || !foundSubLayer.sub_sub_layers) return;
    
    const oldIndex = foundSubLayer.sub_sub_layers.findIndex(ss => ss.id === activeId);
    const newIndex = foundSubLayer.sub_sub_layers.findIndex(ss => ss.id === overId);
    
    if (oldIndex !== -1 && newIndex !== -1) {
      const newSubSubLayers = arrayMove(foundSubLayer.sub_sub_layers, oldIndex, newIndex);
      
      const newLayers = layers.map(l => {
        if (l.id !== foundLayer!.id) return l;
        return {
          ...l,
          sub_layers: l.sub_layers.map(sl => {
            if (sl.id !== subLayerId) return sl;
            return { ...sl, sub_sub_layers: newSubSubLayers };
          })
        };
      });
      setLayers(newLayers);
      
      try {
        const items = newSubSubLayers.map((ss, idx) => ({ id: ss.id, order: idx + 1 }));
        await reorderSubSubLayers(items);
      } catch (e) {
        console.error("Ошибка сохранения порядка:", e);
        await loadLayers();
      }
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-sky-950 to-slate-900 text-white">
        <div className="animate-spin w-8 h-8 border-4 border-sky-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  const getModalTitle = () => {
    switch (addModal.type) {
      case 'layer': return 'Добавить главный слой';
      case 'sublayer': return `Добавить вложенный слой в "${addModal.parentName}"`;
      case 'subsublayer': return `Добавить под-вложенный слой в "${addModal.parentName}"`;
    }
  };

  const getModalPlaceholder = () => {
    switch (addModal.type) {
      case 'layer': return 'Название слоя';
      case 'sublayer': return 'Название вложенного слоя';
      case 'subsublayer': return 'Название под-вложенного слоя';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-sky-950 to-slate-900 text-white px-4 py-4">
      <div className="max-w-7xl mx-auto">
        {/* Навигация */}
        <div className="mb-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 text-sm">
            {/* Группа 1: Регион, Зоны, Пользователи, Журналирование (только для админов) */}
            {isAdmin() && (
              <div className="flex gap-2 rounded-full bg-slate-800/80 p-1">
                <button
                  type="button"
                  onClick={() => (window.location.href = "/admin")}
                  className="px-3 py-1 rounded-full text-slate-300 hover:text-slate-100 hover:bg-slate-700/50 transition-colors"
                >
                  Регион и управление
                </button>
                <button
                  type="button"
                  onClick={() => (window.location.href = "/admin/zones")}
                  className="px-3 py-1 rounded-full text-slate-300 hover:text-slate-100 hover:bg-slate-700/50 transition-colors"
                >
                  Зоны и устройства
                </button>
                <button
                  type="button"
                  onClick={() => (window.location.href = "/admin/users")}
                  className="px-3 py-1 rounded-full text-slate-300 hover:text-slate-100 hover:bg-slate-700/50 transition-colors"
                >
                  Пользователи
                </button>
                <button
                  type="button"
                  onClick={() => (window.location.href = "/admin/journal")}
                  className="px-3 py-1 rounded-full text-slate-300 hover:text-slate-100 hover:bg-slate-700/50 transition-colors"
                >
                  Журналирование
                </button>
              </div>
            )}
            {/* Группа 2: Слои, События */}
            <div className="flex gap-2 rounded-full bg-slate-800/80 p-1">
              <button
                type="button"
                className="px-3 py-1 rounded-full bg-sky-500 text-slate-950 font-medium shadow-sm shadow-sky-500/40"
              >
                Слои
              </button>
              <button
                type="button"
                onClick={() => (window.location.href = "/editor/events")}
                className="px-3 py-1 rounded-full text-slate-300 hover:text-slate-100 hover:bg-slate-700/50 transition-colors"
              >
                События
              </button>
              <button
                type="button"
                onClick={() => { window.location.href = "/editor/reports"; }}
                className="px-3 py-1 rounded-full text-slate-300 hover:text-slate-100 hover:bg-slate-700/50 transition-colors"
              >
                Отчёты
              </button>
            </div>
            {/* Группа 3: Обстановка */}
            <div className="flex gap-2 rounded-full bg-slate-800/80 p-1">
              <button
                type="button"
                onClick={() => (window.location.href = "/situation")}
                className="px-3 py-1 rounded-full text-slate-300 hover:text-slate-100 hover:bg-slate-700/50 transition-colors"
              >
                Обстановка
              </button>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleLogout}
              className="shrink-0 px-3 py-1.5 rounded-lg text-sm text-slate-300 hover:text-red-300 hover:bg-red-500/10 border border-slate-600/50 hover:border-red-500/50 transition-colors"
            >
              Выход
            </button>
          </div>
        </div>

        {/* Заголовок */}
        <h1 className="text-2xl font-semibold tracking-tight mb-3">Слои карты</h1>

        {error && (
          <div className="mb-4 rounded-xl border border-red-500/60 bg-red-500/10 px-4 py-3 text-sm text-red-100">
            {error}
          </div>
        )}

        {/* Список слоев */}
        <div className="rounded-2xl bg-slate-900/80 border border-slate-700/60 shadow-xl shadow-sky-900/40 backdrop-blur p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold">Список слоев</h2>
            <button
              onClick={() => openAddModal('layer')}
              className="w-8 h-8 inline-flex items-center justify-center rounded-lg bg-sky-500 text-slate-900 hover:bg-sky-400 transition"
              title="Добавить главный слой"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
              </svg>
            </button>
          </div>
          
          {layers.length === 0 ? (
            <div className="text-center py-8 text-slate-500 text-sm">
              Слои не созданы. Нажмите + чтобы добавить.
            </div>
          ) : (
            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              onDragEnd={handleLayerDragEnd}
            >
              <SortableContext
                items={layers.map(l => `layer-${l.id}`)}
                strategy={verticalListSortingStrategy}
              >
                <div className="space-y-2">
                  {layers.map((layer) => (
                    <SortableLayerItem
                      key={layer.id}
                      layer={layer}
                      isExpanded={expandedLayers.has(layer.id)}
                      expandedSubLayers={expandedSubLayers}
                      onToggleExpand={toggleExpanded}
                      onToggleVisibility={toggleLayerVisibility}
                      onOpenAddModal={openAddModal}
                      onDelete={(id, name) => openDeleteModal('layer', id, name)}
                      onToggleSubLayerExpand={toggleSubLayerExpanded}
                      onToggleSubLayerVisibility={toggleSubLayerVisibility}
                      onDeleteSubLayer={(id, name) => openDeleteModal('sublayer', id, name)}
                      onToggleSubSubLayerVisibility={toggleSubSubLayerVisibility}
                      onDeleteSubSubLayer={(id, name) => openDeleteModal('subsublayer', id, name)}
                      onSubLayerDragEnd={handleSubLayerDragEnd}
                      onSubSubLayerDragEnd={handleSubSubLayerDragEnd}
                    />
                  ))}
                </div>
              </SortableContext>
            </DndContext>
          )}
        </div>
      </div>

      {/* Модальное окно добавления */}
      <Modal
        open={addModal.open}
        onClose={closeAddModal}
        closeOnEnter={false}
        className="relative bg-slate-900 border border-slate-700 rounded-2xl p-6 max-w-md w-full mx-4 shadow-2xl"
      >
            <h3 className="text-lg font-semibold text-white mb-4">{getModalTitle()}</h3>
            
            {addError && (
              <div className="mb-4 rounded-lg border border-red-500/60 bg-red-500/10 px-3 py-2 text-xs text-red-100">
                {addError}
              </div>
            )}
            
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
              placeholder={getModalPlaceholder()}
              autoFocus
              className="w-full rounded-lg border border-slate-700/70 bg-slate-800 px-3 py-2 text-sm text-slate-50 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500/50 mb-4"
            />
            
            <div className="flex justify-end gap-3">
              <button
                onClick={closeAddModal}
                className="px-4 py-2 rounded-lg text-sm font-medium text-slate-300 hover:text-slate-100 hover:bg-slate-700/50 transition"
              >
                Отмена
              </button>
              <button
                onClick={handleAdd}
                disabled={saving}
                className={`px-4 py-2 rounded-lg text-sm font-medium text-white transition disabled:opacity-60 ${
                  addModal.type === 'layer' ? 'bg-sky-500 hover:bg-sky-600' :
                  addModal.type === 'sublayer' ? 'bg-emerald-500 hover:bg-emerald-600' :
                  'bg-violet-500 hover:bg-violet-600'
                }`}
              >
                {saving ? "..." : "Добавить"}
              </button>
            </div>
      </Modal>

      {/* Модальное окно подтверждения удаления */}
      <Modal
        open={deleteModal.open}
        onClose={() => setDeleteModal({ open: false, type: 'layer', id: null, name: '' })}
        className="relative bg-slate-900 border border-slate-700 rounded-2xl p-6 max-w-md w-full mx-4 shadow-2xl"
      >
            <h3 className="text-lg font-semibold text-white mb-2">Подтверждение удаления</h3>
            <p className="text-slate-300 text-sm mb-6">
              Вы действительно хотите удалить {
                deleteModal.type === 'layer' ? 'слой' : 
                deleteModal.type === 'sublayer' ? 'вложенный слой' : 
                'под-вложенный слой'
              } "{deleteModal.name}"?
              {(deleteModal.type === 'layer' || deleteModal.type === 'sublayer') && (
                <span className="block mt-2 text-amber-400">
                  Все вложенные слои также будут удалены.
                </span>
              )}
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleteModal({ open: false, type: 'layer', id: null, name: '' })}
                className="px-4 py-2 rounded-lg text-sm font-medium text-slate-300 hover:text-slate-100 hover:bg-slate-700/50 transition"
              >
                Отмена
              </button>
              <button
                onClick={confirmDelete}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-red-500 text-white hover:bg-red-600 transition"
              >
                Удалить
              </button>
            </div>
      </Modal>

      {/* Модальное окно успеха */}
      <Modal
        open={successMessage !== null}
        onClose={() => setSuccessMessage(null)}
        className="relative bg-slate-900 border border-green-500/50 rounded-2xl p-6 max-w-md w-full mx-4 shadow-2xl"
      >
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center">
                <span className="text-green-400 text-xl">✓</span>
              </div>
              <h3 className="text-lg font-semibold text-white">Успешно</h3>
            </div>
            <p className="text-slate-300 text-sm mb-6">{successMessage}</p>
            <div className="flex justify-end">
              <button
                onClick={() => setSuccessMessage(null)}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-green-500 text-white hover:bg-green-600 transition"
              >
                OK
              </button>
            </div>
      </Modal>
    </div>
  );
}
