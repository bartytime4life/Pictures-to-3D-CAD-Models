import { useEffect, useId, useMemo, useRef, useState } from 'react';
import { ArrowRight, Command, MagnifyingGlass, X } from '@phosphor-icons/react';
import { useStudioActive } from './StudioActivity';
import { STUDIO_CATALOG, studioFromHash } from './studioCatalog';
import type { Studio } from './studioCatalog';

export type StudioCommand = {
  id: string;
  label: string;
  detail: string;
  keywords?: string;
  run: () => void;
  disabled?: boolean;
};

const navigation: StudioCommand[] = STUDIO_CATALOG.map((item) => ({
  id: item.id,
  label: item.name,
  detail: item.description,
  keywords: item.keywords,
  run: () => {
    window.location.hash = `#${item.id}`;
  },
}));

function currentStudio(): Studio {
  return studioFromHash(window.location.hash);
}

// A shortcut can arrive after the URL changes but before React activates its route.
// Deliver that request to the destination instead of reopening the departing dialog.
let pendingLauncher: string | null = null;

export default function CommandLauncher({
  studio,
  commands = [],
}: {
  studio: Studio;
  commands?: StudioCommand[];
}) {
  const active = useStudioActive();
  const dialog = useRef<HTMLDialogElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const opener = useRef<HTMLButtonElement>(null);
  const previousFocus = useRef<HTMLElement | null>(null);
  const id = useId();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState(0);
  const available = useMemo(
    () => [
      ...commands,
      ...navigation,
      ...(!commands.some((command) => command.id === 'project-library')
        ? [
            {
              id: 'project-library',
              label: 'Open saved flat-part projects',
              detail: 'Resume browser snapshots and print history in the flat-part workbench',
              keywords: 'library project resume saved history',
              run: () => {
                window.location.hash = '#workbench?open=projects';
              },
            },
          ]
        : []),
    ],
    [commands],
  );
  const matches = available.filter((command) =>
    `${command.label} ${command.detail} ${command.keywords ?? ''}`
      .toLowerCase()
      .includes(query.trim().toLowerCase()),
  );
  const results = query.trim()
    ? [
        ...matches,
        {
          id: 'search-knowledge',
          label: `Search knowledge for “${query.trim()}”`,
          detail: 'Look through the built-in guides and explanations',
          run: () => {
            const requestedHash = `#knowledge?search=${encodeURIComponent(query.trim())}`;
            if (window.location.hash === requestedHash) {
              // A guide search may have been edited locally since this URL was set.
              // Explicitly replay the route request when the browser would emit no event.
              window.dispatchEvent(
                new HashChangeEvent('hashchange', {
                  oldURL: window.location.href,
                  newURL: window.location.href,
                }),
              );
            } else window.location.hash = requestedHash;
          },
        },
      ]
    : matches;
  const openLauncher = () => {
    if (!active || currentStudio() !== studio) return;
    previousFocus.current =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setQuery('');
    setSelected(0);
    setOpen(true);
  };
  const run = (command: StudioCommand) => {
    if (command.disabled) return;
    setOpen(false);
    dialog.current?.close();
    command.run();
  };

  useEffect(() => {
    if (!active) {
      setOpen(false);
      return;
    }
    if (pendingLauncher === studio && currentStudio() === studio) {
      pendingLauncher = null;
      openLauncher();
    }
    const keydown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        if (currentStudio() !== studio) {
          event.preventDefault();
          pendingLauncher = currentStudio();
          return;
        }
        // A native dialog already owns focus; do not stack another modal over it.
        if (document.querySelector('dialog[open]') && !dialog.current?.open) return;
        event.preventDefault();
        openLauncher();
      }
    };
    window.addEventListener('keydown', keydown);
    return () => window.removeEventListener('keydown', keydown);
  }, [active, studio]);
  useEffect(() => {
    if (open && active) {
      dialog.current?.showModal();
      input.current?.focus();
    } else dialog.current?.close();
  }, [open, active]);
  useEffect(() => {
    if (!open) return;
    dialog.current
      ?.querySelector(`[data-command-index="${selected}"]`)
      ?.scrollIntoView({ block: 'nearest' });
  }, [selected, open]);

  return (
    <>
      <button ref={opener} type="button" className="command-trigger" onClick={openLauncher}>
        <MagnifyingGlass size={19} aria-hidden="true" />
        <span className="command-trigger-label">
          Search commands<span className="sr-only"> and help</span>
        </span>{' '}
        <kbd aria-hidden="true">
          <Command size={12} /> K
        </kbd>
      </button>
      <dialog
        ref={dialog}
        className="command-dialog"
        aria-labelledby={`${id}-title`}
        onCancel={() => setOpen(false)}
        onClose={() => {
          // A queued native close event must not dismiss a just-reopened dialog.
          if (dialog.current?.open) return;
          setOpen(false);
          if (!active || currentStudio() !== studio) return;
          const previous = previousFocus.current;
          if (
            previous?.isConnected &&
            !previous.closest('[hidden], [inert]') &&
            !previous.matches(':disabled')
          )
            previous.focus();
          else opener.current?.focus();
        }}
        onClick={(event) => {
          if (event.target === event.currentTarget) setOpen(false);
        }}
      >
        <div className="command-surface">
          <div className="command-heading">
            <h2 id={`${id}-title`}>Where do you want to go?</h2>
            <button
              type="button"
              className="icon-button"
              aria-label="Close command search"
              onClick={() => setOpen(false)}
            >
              <X size={20} />
            </button>
          </div>
          <div className="command-search">
            <MagnifyingGlass size={23} aria-hidden="true" />
            <input
              ref={input}
              value={query}
              placeholder="Find a tool, action or guide…"
              aria-label="Search commands"
              role="combobox"
              aria-expanded="true"
              aria-controls={`${id}-results`}
              aria-autocomplete="list"
              aria-activedescendant={
                results[selected] ? `${id}-${results[selected].id}` : undefined
              }
              onChange={(event) => {
                setQuery(event.target.value);
                setSelected(0);
              }}
              onKeyDown={(event) => {
                if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
                  event.preventDefault();
                  setSelected((value) =>
                    Math.max(
                      0,
                      Math.min(results.length - 1, value + (event.key === 'ArrowDown' ? 1 : -1)),
                    ),
                  );
                } else if (event.key === 'Enter' && results[selected]) {
                  event.preventDefault();
                  run(results[selected]);
                }
              }}
            />
          </div>
          <p className="command-group-label">
            {query ? 'Matching actions' : 'Your tools & workspaces'}
          </p>
          <ul
            id={`${id}-results`}
            className="command-results"
            role="listbox"
            aria-label="Available commands"
          >
            {results.map((command, index) => (
              <li
                id={`${id}-${command.id}`}
                key={command.id}
                role="option"
                aria-selected={selected === index}
                aria-disabled={command.disabled}
                data-command-index={index}
                className={selected === index ? 'selected' : ''}
                onMouseMove={() => setSelected(index)}
                onClick={() => run(command)}
              >
                <span>
                  <strong>{command.label}</strong>
                  <small>{command.detail}</small>
                </span>
                <ArrowRight size={19} aria-hidden="true" />
              </li>
            ))}
          </ul>
          <div className="command-footer">
            <span>
              <kbd>↑</kbd> <kbd>↓</kbd> to explore · <kbd>Enter</kbd> to open
            </span>
            <span>
              <kbd>Esc</kbd> to close
            </span>
          </div>
        </div>
      </dialog>
    </>
  );
}
