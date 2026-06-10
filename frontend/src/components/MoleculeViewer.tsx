import { useEffect, useRef, useState } from 'react'
import { createViewer, type GLViewer } from '3dmol'
import { Button } from './ui/button'

type PointCharge = { x: number; y: number; z: number; charge_e: number }

type MoleculeViewerProps = {
  molBlock?: string | null
  densityCube?: string | null
  pointCharges?: PointCharge[] | null
}

type DisplayMode = 'stick' | 'sphere' | 'combined'

export function MoleculeViewer({ molBlock, densityCube, pointCharges }: MoleculeViewerProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const viewerRef = useRef<GLViewer | null>(null)
  const [displayMode, setDisplayMode] = useState<DisplayMode>('combined')
  const [selectedAtom, setSelectedAtom] = useState<string | null>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container || !molBlock) return

    container.replaceChildren()
    const viewer = createViewer(container, { backgroundColor: '#020617' })
    viewerRef.current = viewer
    viewer.addModel(molBlock, 'sdf')
    viewer.setClickable({}, true, (atom: { elem?: string; index?: number }, activeViewer: GLViewer) => {
      activeViewer.setStyle({}, moleculeStyle(displayMode))
      activeViewer.setStyle(
        { index: atom.index },
        { sphere: { scale: 0.48, color: '#22d3ee' }, stick: { radius: 0.2, color: '#22d3ee' } },
      )
      activeViewer.render()
      setSelectedAtom(`${atom.elem ?? 'Atom'} ${Number(atom.index ?? 0) + 1}`)
    })
    viewer.setStyle({}, moleculeStyle(displayMode))

    if (densityCube) {
      viewer.addVolumetricData(densityCube, 'cube', {
        isoval: 0.02,
        color: '#22d3ee',
        opacity: 0.38,
      })
    }
    for (const charge of pointCharges ?? []) {
      viewer.addSphere({
        center: { x: charge.x, y: charge.y, z: charge.z },
        radius: 0.24 + Math.abs(charge.charge_e) * 0.5,
        color: charge.charge_e >= 0 ? '#f59e0b' : '#60a5fa',
        alpha: 0.8,
      })
    }
    viewer.zoomTo()
    viewer.resize()
    viewer.render()

    const observer = new ResizeObserver(() => {
      viewer.resize()
      viewer.render()
    })
    observer.observe(container)

    return () => {
      observer.disconnect()
      viewer.clear()
      container.replaceChildren()
      viewerRef.current = null
    }
  }, [molBlock, densityCube, pointCharges, displayMode])

  if (!molBlock) {
    return <div className="flex h-96 items-center justify-center text-sm text-slate-500">Подготовьте молекулу, чтобы открыть интерактивную 3D-сцену.</div>
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex gap-2">
          <Button variant={displayMode === 'combined' ? 'default' : 'secondary'} onClick={() => setDisplayMode('combined')}>Шаростержневая</Button>
          <Button variant={displayMode === 'stick' ? 'default' : 'secondary'} onClick={() => setDisplayMode('stick')}>Стержни</Button>
          <Button variant={displayMode === 'sphere' ? 'default' : 'secondary'} onClick={() => setDisplayMode('sphere')}>Сферы</Button>
        </div>
        <div className="text-xs text-slate-400">{selectedAtom ? `Выбран: ${selectedAtom}` : 'Нажмите на атом для выделения'}</div>
      </div>
      <div className="molecule-viewer-shell">
        <div ref={containerRef} className="molecule-viewer-canvas" />
      </div>
    </div>
  )
}

function moleculeStyle(mode: DisplayMode) {
  if (mode === 'stick') return { stick: { radius: 0.16, colorscheme: 'Jmol' as const } }
  if (mode === 'sphere') return { sphere: { scale: 0.7, colorscheme: 'Jmol' as const } }
  return {
    stick: { radius: 0.14, colorscheme: 'Jmol' as const },
    sphere: { scale: 0.28, colorscheme: 'Jmol' as const },
  }
}
