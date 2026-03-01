/**
 * Mutation hook that triggers the backend calculation.
 *
 * Design decisions:
 *  - Debounce (600 ms): avoids firing a calculation request on every keystroke
 *    while the user is still typing a span length or load value.
 *  - State updates (isCalculating, results, calculationError) are written
 *    directly to the Zustand store so all components can react without prop
 *    drilling.
 *  - The request body is read lazily from the store at mutation time (not at
 *    hook call time) so it always reflects the current form state.
 */

import { useRef, useCallback } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useBeamStore } from "@/stores/useBeamStore";
import type { CalculationRequest, CalculationResponse } from "@/types/beam";

/** Debounce delay in milliseconds before the API call is fired */
const DEBOUNCE_MS = 600;

export function useCalculation() {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const mutation = useMutation({
    mutationFn: (request: CalculationRequest) =>
      api.post<CalculationResponse>("/api/calculate", request),

    onMutate: () => {
      // Clear previous results and mark as loading before the request starts
      useBeamStore.getState().setIsCalculating(true);
      useBeamStore.getState().setCalculationError(null);
    },

    onSuccess: (data) => {
      useBeamStore.getState().setResults(data);
      useBeamStore.getState().setIsCalculating(false);
    },

    onError: (error: Error) => {
      useBeamStore.getState().setCalculationError(error.message);
      useBeamStore.getState().setIsCalculating(false);
    },
  });

  /**
   * Call this whenever any form value changes.
   * The actual API request is debounced by DEBOUNCE_MS ms so rapid changes
   * (e.g. typing a span length digit by digit) only trigger one calculation.
   */
  const triggerCalculation = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }
    timerRef.current = setTimeout(() => {
      const request = useBeamStore.getState().buildRequest();
      mutation.mutate(request);
    }, DEBOUNCE_MS);
  }, [mutation]);

  return { triggerCalculation, ...mutation };
}
