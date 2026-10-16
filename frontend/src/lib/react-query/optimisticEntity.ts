import type { QueryClient, QueryKey } from '@tanstack/react-query';

interface OptimisticEntityContext<TList> {
  previousList?: TList;
}

interface OptimisticEntityOptions<TEntity extends { id: string }, TList, TVariables, TResult> {
  queryClient: QueryClient;
  listQueryKey: QueryKey;
  detailQueryKey: (entityId: string) => QueryKey;
  mutationLabel: (variables: TVariables) => string;
  getEntityId: (variables: TVariables) => string;
  getOptimisticEntity: (entity: TEntity, variables: TVariables, optimisticUpdatedAt: string) => TEntity;
  getListItems: (list: TList) => TEntity[];
  setListItems: (list: TList, items: TEntity[]) => TList;
  mergeServerEntity?: (current: TEntity, result: TResult) => TEntity;
  onError?: (error: any, variables: TVariables) => void;
}

export function createOptimisticEntityHandlers<
  TEntity extends { id: string },
  TList,
  TVariables,
  TResult extends TEntity
>({
  queryClient,
  listQueryKey,
  detailQueryKey,
  mutationLabel,
  getEntityId,
  getOptimisticEntity,
  getListItems,
  setListItems,
  mergeServerEntity,
  onError,
}: OptimisticEntityOptions<TEntity, TList, TVariables, TResult>) {
  return {
    onMutate: async (variables: TVariables): Promise<OptimisticEntityContext<TList>> => {
      const entityId = getEntityId(variables);
      await queryClient.cancelQueries({ queryKey: listQueryKey });
      const previousList = queryClient.getQueryData<TList>(listQueryKey);
      const optimisticUpdatedAt = new Date().toISOString();

      queryClient.setQueryData<TList | undefined>(listQueryKey, (current) => {
        if (!current) return current;
        const items = getListItems(current).map((entity) =>
          entity.id === entityId
            ? getOptimisticEntity(entity, variables, optimisticUpdatedAt)
            : entity
        );
        return setListItems(current, items);
      });

      queryClient.setQueryData<TEntity | undefined>(detailQueryKey(entityId), (current) =>
        current ? getOptimisticEntity(current, variables, optimisticUpdatedAt) : current
      );

      return { previousList };
    },
    onError: (error: any, variables: TVariables, context?: OptimisticEntityContext<TList>) => {
      if (context?.previousList) {
        queryClient.setQueryData(listQueryKey, context.previousList);
      }
      onError?.(error, variables);
    },
    onSuccess: (result: TResult) => {
      queryClient.setQueryData<TEntity | undefined>(detailQueryKey(result.id), (current) =>
        current && mergeServerEntity ? mergeServerEntity(current, result) : result
      );
      queryClient.setQueryData<TList | undefined>(listQueryKey, (current) => {
        if (!current) return current;
        const items = getListItems(current).map((entity) =>
          entity.id === result.id
            ? mergeServerEntity
              ? mergeServerEntity(entity, result)
              : result
            : entity
        );
        return setListItems(current, items);
      });
    },
    onSettled: (_result: TResult | undefined, _error: unknown, variables: TVariables) => {
      const entityId = getEntityId(variables);
      queryClient.invalidateQueries({ queryKey: listQueryKey });
      queryClient.invalidateQueries({ queryKey: detailQueryKey(entityId) });
    },
  };
}
