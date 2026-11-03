/** A primeira letra de cada parte do nome fica maiúscula. O restante fica como foi escrito. */
export function capitalizeChildName(value: string): string {
  return value.replace(
    /(^|[\s-])(\p{L})/gu,
    (_, separator: string, letter: string) => separator + letter.toLocaleUpperCase(),
  );
}
