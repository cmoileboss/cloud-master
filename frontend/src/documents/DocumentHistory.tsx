import { Group, Paper, Stack, Text, Title } from '@mantine/core';
import { useQuery } from '@tanstack/react-query';
import { get } from '../api';
import { formatDate } from '../types';
import type { ConvocationDocument } from '../types';
import DownloadButton from './DownloadButton';

/** Convocations enregistrées : informations en base de données, fichiers dans le stockage. */
export default function DocumentHistory() {
  const documents = useQuery({
    queryKey: ['documents'],
    queryFn: () => get<ConvocationDocument[]>('/api/documents'),
  });

  return (
    <Stack gap="sm">
      <Title order={2} size="h4">
        Convocations générées
      </Title>
      {documents.error && <Text c="red">{documents.error.message}</Text>}
      {documents.data?.length === 0 && (
        <Text size="sm" c="dimmed">
          Aucune convocation pour l'instant.
        </Text>
      )}
      {documents.data?.map((document) => (
        <Paper key={document.id} withBorder p="sm">
          <Group justify="space-between">
            <div>
              <Text size="sm" fw={600}>
                {document.title}
              </Text>
              <Text size="xs" c="dimmed">
                Réunion du {formatDate(document.meeting_date)} · générée le{' '}
                {formatDate(document.created_at)}
              </Text>
            </div>
            <DownloadButton document={document} size="xs" variant="light" />
          </Group>
        </Paper>
      ))}
    </Stack>
  );
}
