import { useState } from 'react';
import type { FormEvent } from 'react';
import { Alert, Button, Group, Paper, Stack, Text, Textarea, Title } from '@mantine/core';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { IconSparkles } from '@tabler/icons-react';
import { get, post, showError } from '../api';
import { formatDate, formatMonth, formatTime } from '../types';
import type { ConvocationResult, Meeting } from '../types';
import ConvocationPreview from './ConvocationPreview';
import DocumentHistory from './DocumentHistory';

export default function DocumentsPage() {
  const queryClient = useQueryClient();
  const [request, setRequest] = useState(
    'Prépare la convocation pour la prochaine réunion de la CSDGE.',
  );

  const meetings = useQuery({
    queryKey: ['meetings'],
    queryFn: () => get<Meeting[]>('/api/meetings'),
  });
  const generate = useMutation({
    mutationFn: () => post<ConvocationResult>('/api/documents/generate', { request }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['documents'] }),
    onError: showError,
  });
  const result = generate.data;

  function submit(event: FormEvent) {
    event.preventDefault();
    generate.mutate();
  }

  return (
    <Stack gap="xl" className="documents-page">
      <div>
        <Title order={1}>Créer une convocation</Title>
        <Text c="dimmed">
          Décrivez votre besoin : l'IA retrouve la réunion dans le calendrier et rédige
          l'introduction.
        </Text>
      </div>

      <Paper withBorder p="lg">
        <form onSubmit={submit}>
          <Stack gap="md">
            <Textarea
              label="Votre demande"
              autosize
              minRows={3}
              maxLength={3000}
              value={request}
              onChange={(event) => setRequest(event.currentTarget.value)}
            />
            <Group gap="xs">
              <Text size="xs" c="dimmed">
                Exemples :
              </Text>
              {meetings.data?.map((meeting) => (
                <Button
                  key={meeting.id}
                  size="xs"
                  variant="default"
                  onClick={() =>
                    setRequest(
                      `Prépare la convocation pour la réunion de ${formatMonth(meeting.meeting_date)}.`,
                    )
                  }
                >
                  Réunion de {formatMonth(meeting.meeting_date)}
                </Button>
              ))}
            </Group>

            <details className="calendar">
              <summary>Voir le calendrier source</summary>
              {meetings.error && <Text c="red">{meetings.error.message}</Text>}
              {meetings.data?.map((meeting) => (
                <Text key={meeting.id} size="sm" mt="xs">
                  <strong>{meeting.title}</strong> — {formatDate(meeting.meeting_date)},{' '}
                  {formatTime(meeting.start_time)}–{formatTime(meeting.end_time)},{' '}
                  {meeting.location}
                </Text>
              ))}
            </details>

            <Group justify="flex-end">
              <Button
                type="submit"
                leftSection={<IconSparkles size={18} />}
                loading={generate.isPending}
                disabled={request.trim().length < 5}
              >
                Générer la convocation
              </Button>
            </Group>
          </Stack>
        </form>
      </Paper>

      {result?.clarification && (
        <Alert color="orange" title="Précisez votre demande">
          {result.clarification}
        </Alert>
      )}
      {result?.document && result.meeting && (
        <ConvocationPreview
          document={result.document}
          meeting={result.meeting}
          text={result.text}
        />
      )}

      <DocumentHistory />
    </Stack>
  );
}
