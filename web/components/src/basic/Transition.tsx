import {
  Alert,
  Button,
  Container,
  Flex,
  Loader,
  Stack,
  Text,
} from "@mantine/core";
import { useNavigate } from "react-router";
import { IconInfoCircle } from "@tabler/icons-react";

export const NotFound = ({ message }: { message?: string }) => {
  const navigate = useNavigate();

  return (
    <Container
      size="xs"
      style={{
        height: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <Alert
        color="red"
        title="Not Found"
        variant="404 - Not Found"
        icon={<IconInfoCircle size={12} stroke={1.5} />}
      >
        <Stack align="flex-start">
          {message || "Sorry, the page you are looking for does not exist."}
          <Button variant="filled" onClick={() => navigate("/")} size="xs">
            Back Home
          </Button>
        </Stack>
      </Alert>
    </Container>
  );
};

export const NotFoundSubPage = ({ message }: { message?: string }) => {
  return (
    <Alert
      color="red"
      title="Not Found"
      variant="404 - Not Found"
      icon={<IconInfoCircle size={12} stroke={1.5} />}
    >
      {message || "Sorry, the page you are looking for does not exist."}
    </Alert>
  );
};

export const NotFoundInline = ({ message }: { message?: string }) => {
  return (
    <Text c="red" size="sm">
      {message || "Not Found"}
    </Text>
  );
};

export const Loading = ({ tip }: { tip?: string }) => {
  if (tip === undefined) {
    return (
      <Flex justify="center" align="center">
        <Loader color="blue" size="md" />
      </Flex>
    );
  }

  return (
    <Flex
      gap="md"
      direction="column"
      justify="center"
      align="center"
      style={{ height: "100%" }}
    >
      <Loader color="blue" size="md" />
      {tip}
    </Flex>
  );
};

export const LoadingInline = ({ tip }: { tip?: string }) => {
  if (tip === undefined) {
    return <Loader color="blue" size="xs" />;
  }
  return (
    <Flex gap="md" direction="column" justify="center" align="center">
      <Loader color="blue" size="xs" />
      {tip}
    </Flex>
  );
};

export const NotAuthorized = ({ message }: { message?: string }) => {
  return (
    <Alert
      color="red"
      title="Not Found"
      variant="403 - Not Authorized"
      icon={<IconInfoCircle size={12} stroke={1.5} />}
    >
      {message || "Sorry, you are not authorized to access this page."}
    </Alert>
  );
};
