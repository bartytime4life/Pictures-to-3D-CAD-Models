import { createContext, useContext } from 'react';

/** Visited studios remain mounted; inactive ones must not take focus or start work. */
export const StudioActivity = createContext(true);
export const useStudioActive = () => useContext(StudioActivity);
