import { DisplayInterface } from ".";
import { Checkbox } from "@mantine/core";
import { MultiLingualString } from "../../basic";

const label = {
  yes: {
    lang2value: {
      en: "Yes",
      vi: "Có",
    },
    lang: "en",
  },
  no: {
    lang2value: {
      en: "No",
      vi: "Không",
    },
    lang: "en",
  },
};

export const BooleanDisplay = ({ value }: DisplayInterface<boolean>) => {
  return (
    <Checkbox
      checked={value}
      label={<MultiLingualString value={label[value ? "yes" : "no"]} />}
      readOnly={true}
    />
  );
};
