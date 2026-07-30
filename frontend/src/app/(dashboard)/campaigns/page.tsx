"use client";

export default function CampaignsPage() {
  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            Campañas
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Crea y gestiona campañas multicanal
          </p>
        </div>
        <button className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700">
          Nueva Campaña
        </button>
      </div>

      <div className="rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-center py-12">
          <p className="text-gray-500 dark:text-gray-400">
            No hay campañas aún. Crea tu primera campaña para comenzar.
          </p>
        </div>
      </div>
    </div>
  );
}
