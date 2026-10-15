import { Group, Paper, Text } from '@mantine/core';
import { formatDate, formatTime } from '../types';
import type { ConvocationDocument, Meeting } from '../types';
import DownloadButton from './DownloadButton';

type Props = { document: ConvocationDocument; meeting: Meeting; text: string };

/** Aperçu fidèle au PDF (backend/app/pdf.py) : faits du calendrier + texte rédigé par l'IA. */
export default function ConvocationPreview({ document, meeting, text }: Props) {
  return (
    <Paper withBorder p="lg" className="convocation-result" aria-label="Convocation générée">
      <Group justify="space-between" mb="md">
        <div>
          <Text fw={600}>Votre convocation est prête</Text>
          <Text size="xs" c="dimmed">
            Relisez-la avant de télécharger le PDF.
          </Text>
        </div>
        <DownloadButton document={document} />
      </Group>

      <article className="letter">
        <div className="letter-brand">FFK / SERVICE DES GRADES</div>
        <Text size="xs" c="dimmed">
          DOCUMENT PÉDAGOGIQUE FICTIF
        </Text>
        <h2>Convocation — {meeting.title}</h2>
        <p>À l'attention de : {meeting.recipients.join('; ')}</p>
        <p>
          <strong>{formatDate(meeting.meeting_date)}</strong> · {formatTime(meeting.start_time)} –{' '}
          {formatTime(meeting.end_time)}
          <br />
          {meeting.location}
        </p>
        <p className="letter-text">{text}</p>
        <strong>Ordre du jour</strong>
        <ol>
          {meeting.agenda.map((point) => (
            <li key={point}>{point}</li>
          ))}
        </ol>
        <p>
          Merci de confirmer votre présence avant le {formatDate(meeting.confirmation_date)} auprès
          de {meeting.contact}.
        </p>
        <p>
          Cordialement,
          <br />
          Le secrétariat des grades
        </p>
      </article>
    </Paper>
  );
}
